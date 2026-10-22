"""Wire v1: verify the exact signed UTF-8 bytes, never reserialize to verify."""
import base64
import hashlib
import json
import time
from typing import Literal
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, ConfigDict, Field, model_validator

DOMAIN = b"RescueLink/v1:"
MAX_TTL_MS = 86_400_000
MAX_FUTURE_MS = 300_000


class SOSBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    protocol_version: Literal[1]
    incident_id: str
    origin_key_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at_ms: int
    expires_at_ms: int
    priority: int = Field(ge=1, le=3)
    hop_limit: int = Field(ge=1, le=8)
    text: str = Field(min_length=3, max_length=1000)
    location_text: str = Field(min_length=1, max_length=250)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    location_captured_at_ms: int | None = None
    people_count: int = Field(ge=1, le=1000)
    needs: list[Literal["medical", "evacuation", "food", "water", "other"]] = Field(max_length=5)
    is_drill: Literal[True]

    @model_validator(mode="after")
    def check_fields(self):
        UUID(self.incident_id)
        if not self.text.strip() or not self.location_text.strip():
            raise ValueError("Text and location cannot be blank")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Both coordinates are required together")
        if not 0 < self.expires_at_ms - self.created_at_ms <= MAX_TTL_MS:
            raise ValueError("Lifetime must be positive and at most 24 hours")
        if self.location_captured_at_ms is not None and self.location_captured_at_ms > self.created_at_ms + MAX_FUTURE_MS:
            raise ValueError("Location timestamp is in the future")
        return self


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    body_b64: str = Field(max_length=14000)
    public_key_b64: str = Field(max_length=512)
    signature_b64: str = Field(max_length=256)
    hop_count: int = Field(ge=0, le=8)


def decode_b64(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON key")
        out[key] = value
    return out


def verify_envelope(envelope: Envelope, now_ms: int | None = None, *, check_expiry=True) -> SOSBody:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    raw = decode_b64(envelope.body_b64)
    if len(raw) > 10000 or hashlib.sha256(raw).hexdigest() != envelope.message_id:
        raise ValueError("Message hash does not match")
    public_der = decode_b64(envelope.public_key_b64)
    public_key = serialization.load_der_public_key(public_der)
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError("Only ECDSA P-256 is supported")
    try:
        public_key.verify(decode_b64(envelope.signature_b64), DOMAIN + raw, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise ValueError("Invalid signature") from exc
    body = SOSBody.model_validate(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object))
    if hashlib.sha256(public_der).hexdigest() != body.origin_key_id:
        raise ValueError("Origin key does not match")
    if envelope.hop_count > body.hop_limit:
        raise ValueError("Hop limit exceeded")
    if body.created_at_ms > now_ms + MAX_FUTURE_MS:
        raise ValueError("Device clock is too far in the future")
    if check_expiry and body.expires_at_ms <= now_ms:
        raise TimeoutError("Message expired")
    return body
