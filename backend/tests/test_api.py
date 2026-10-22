import base64
import hashlib
import json
import time
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.main import create_app
from app.protocol import DOMAIN, Envelope, verify_envelope

ADMIN = "a" * 40
GATEWAY = "g" * 40
AUTH = {"Authorization": "Bearer " + ADMIN}
UPLOAD = {"X-Drill-Key": GATEWAY}


def packet(**overrides):
    key = overrides.pop("_key", None) or ec.generate_private_key(ec.SECP256R1())
    der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    now = int(time.time() * 1000)
    body = dict(protocol_version=1, incident_id=str(uuid.uuid4()), origin_key_id=hashlib.sha256(der).hexdigest(),
                created_at_ms=now, expires_at_ms=now+3600000, priority=2, hop_limit=8,
                text="Diễn tập: cần sơ tán ba người", location_text="Điểm diễn tập A", latitude=16.07,
                longitude=108.2, accuracy_m=20.0, location_captured_at_ms=now, people_count=3,
                needs=["evacuation"], is_drill=True)
    body.update(overrides)
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    b64 = lambda x: base64.b64encode(x).decode()
    return dict(message_id=hashlib.sha256(raw).hexdigest(), body_b64=b64(raw), public_key_b64=b64(der),
                signature_b64=b64(key.sign(DOMAIN+raw, ec.ECDSA(hashes.SHA256()))), hop_count=0)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGE_MODEL", str(tmp_path / "missing.json"))
    with TestClient(create_app(f"sqlite:///{tmp_path}/test.db", ADMIN, GATEWAY)) as c:
        yield c


def test_auth_boundaries(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/v1/sos").status_code == 401
    assert client.get("/api/v1/sos", headers=UPLOAD).status_code == 401
    assert client.post("/api/v1/sos", json=packet()).status_code == 401


def test_duplicate_has_one_incident_and_one_audit(client):
    p = packet()
    first = client.post("/api/v1/sos", json=p, headers=UPLOAD)
    second = client.post("/api/v1/sos", json=p, headers=UPLOAD)
    assert first.status_code == 201 and second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["received_at_ms"] == second.json()["received_at_ms"]
    assert client.get("/api/v1/sos", headers=AUTH).json()["total"] == 1
    assert len(client.get(f"/api/v1/sos/{p['message_id']}/events", headers=AUTH).json()) == 1


@pytest.mark.parametrize("change", ["hash", "signature", "payload"])
def test_tampering_rejected(client, change):
    p = packet()
    if change == "hash": p["message_id"] = "0" * 64
    if change == "signature": p["signature_b64"] = base64.b64encode(b"invalid").decode()
    if change == "payload":
        raw = base64.b64decode(p["body_b64"]).replace(b'"priority":2', b'"priority":1')
        p["body_b64"] = base64.b64encode(raw).decode()
        p["message_id"] = hashlib.sha256(raw).hexdigest()
    assert client.post("/api/v1/sos", json=p, headers=UPLOAD).status_code == 422


def test_expired_message_not_created(client):
    now = int(time.time()*1000)
    assert client.post("/api/v1/sos", json=packet(created_at_ms=now-20000, expires_at_ms=now-1000), headers=UPLOAD).status_code == 410


@pytest.mark.parametrize("fields", [dict(is_drill=False),dict(priority=0),dict(latitude=91.0),dict(longitude=None),dict(text="   "),dict(people_count=0),dict(expires_at_ms=9999999999999),dict(created_at_ms=9999999999999,expires_at_ms=10000000099999)])
def test_invalid_signed_body_rejected(client, fields):
    assert client.post("/api/v1/sos", json=packet(**fields), headers=UPLOAD).status_code == 422


def test_hop_limit(client):
    p = packet(); p["hop_count"] = 8
    assert client.post("/api/v1/sos", json=p, headers=UPLOAD).status_code == 201
    p["hop_count"] = 9
    assert client.post("/api/v1/sos", json=p, headers=UPLOAD).status_code == 422


def test_incident_collision_is_not_silent_overwrite(client):
    incident = str(uuid.uuid4())
    assert client.post("/api/v1/sos", json=packet(incident_id=incident), headers=UPLOAD).status_code == 201
    assert client.post("/api/v1/sos", json=packet(incident_id=incident), headers=UPLOAD).status_code == 409


def test_operator_workflow_and_conflict(client):
    p = packet(); client.post("/api/v1/sos", json=p, headers=UPLOAD)
    endpoint = f"/api/v1/sos/{p['message_id']}"
    assert client.patch(endpoint, headers=AUTH,json=dict(version=1,status="RESOLVED")).status_code == 422
    assert client.patch(endpoint, headers=AUTH,json=dict(version=1,status="VERIFIED")).status_code == 200
    assert client.patch(endpoint, headers=AUTH,json=dict(version=1,status="ASSIGNED",assigned_team="Đội 1")).status_code == 409
    assert client.patch(endpoint, headers=AUTH,json=dict(version=2,status="ASSIGNED")).status_code == 422
    assert client.patch(endpoint, headers=AUTH,json=dict(version=2,status="ASSIGNED",assigned_team="Đội 1")).status_code == 200
    assert client.patch(endpoint, headers=AUTH,json=dict(version=3,status="RESOLVED")).status_code == 200


def test_rules_never_downgrade_claim(client):
    p = packet(priority=1, needs=["food"])
    client.post("/api/v1/sos", json=p, headers=UPLOAD)
    row = client.get("/api/v1/sos", headers=AUTH).json()["items"][0]
    assert row["ai"]["suggested_priority"] == 1
    assert row["ai"]["confidence"] is None and row["ai"]["requires_review"] is True


def test_persistence_after_application_restart(tmp_path):
    url = f"sqlite:///{tmp_path}/persistent.db"
    p = packet()
    with TestClient(create_app(url,ADMIN,GATEWAY)) as c:
        assert c.post("/api/v1/sos", json=p, headers=UPLOAD).status_code == 201
    with TestClient(create_app(url,ADMIN,GATEWAY)) as c:
        assert c.get("/api/v1/sos", headers=AUTH).json()["items"][0]["message_id"] == p["message_id"]


def test_request_size_limit(client):
    assert client.post("/api/v1/sos", content=b"x"*33000, headers=UPLOAD).status_code == 413


def test_signature_independent_of_relay_metadata():
    p=packet()
    p["hop_count"]=3
    assert verify_envelope(Envelope(**p)).priority == 2


def test_json_key_order_is_not_changed_for_signature_verification():
    assert verify_envelope(Envelope(**packet())).is_drill is True
