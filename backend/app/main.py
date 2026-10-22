import hmac
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update, text
from sqlalchemy.exc import IntegrityError

from .database import AuditEvent, Incident, connect_database
from .protocol import Envelope, verify_envelope
from .triage import suggest


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    status: Literal["NEW", "VERIFIED", "ASSIGNED", "RESOLVED"]
    assigned_team: str | None = Field(default=None, max_length=100)


def create_app(database_url=None, admin_token=None, drill_key=None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./rescue.db")
    admin = admin_token or os.getenv("ADMIN_TOKEN", "")
    gateway_key = drill_key or os.getenv("DRILL_KEY", "")
    if len(admin) < 24 or len(gateway_key) < 24 or admin.startswith("REPLACE_") or gateway_key.startswith("REPLACE_"):
        raise RuntimeError("Run scripts/setup.py; ADMIN_TOKEN and DRILL_KEY require at least 24 characters")

    @asynccontextmanager
    async def lifespan(app):
        engine, factory = connect_database(url)
        app.state.session_factory = factory
        yield
        engine.dispose()

    app = FastAPI(title="RescueLink — DIỄN TẬP", version="0.2.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.middleware("http")
    async def bound_request_size(request, call_next):
        # Also enforced at nginx; protects direct development API access.
        if request.method in {"POST", "PUT", "PATCH"}:
            chunks = []
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 32768:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def session():
        with app.state.session_factory() as db:
            yield db

    def require_admin(authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, "Bearer " + admin):
            raise HTTPException(401, "Dashboard token không hợp lệ")

    def require_gateway(x_drill_key: str = Header(default="")):
        if not hmac.compare_digest(x_drill_key, gateway_key):
            raise HTTPException(401, "Drill key không hợp lệ")

    def view(row):
        return {
            "message_id": row.message_id, "incident_id": row.incident_id,
            "body": row.body, "effective_priority": row.priority, "status": row.status, "assigned_team": row.assigned_team,
            "version": row.version, "received_at_ms": row.received_at_ms, "ai": row.ai,
        }

    def receipt(row, duplicate):
        return {"message_id": row.message_id, "status": "SERVER_RECEIVED", "duplicate": duplicate,
                "received_at_ms": row.received_at_ms, "scope": "core-text-only", "signed": False}

    @app.get("/api/health")
    def health(db=Depends(session)):
        db.execute(select(1))
        return {"status": "ok", "version": "0.2.0", "mode": "DRILL_ONLY"}

    @app.post("/api/v1/sos", dependencies=[Depends(require_gateway)])
    def ingest(envelope: Envelope, db=Depends(session)):
        try:
            body = verify_envelope(envelope, check_expiry=False)
        except Exception as exc:
            raise HTTPException(422, "Envelope/chữ ký không hợp lệ") from exc
        existing = db.get(Incident, envelope.message_id)
        if existing:
            return receipt(existing, True)  # retry accepted even after original expiry
        now = int(time.time() * 1000)
        if body.expires_at_ms <= now:
            raise HTTPException(410, "SOS đã hết thời hạn chuyển tiếp")
        if db.bind.dialect.name == "postgresql":
            # Serialize count+insert for one signing key across API workers.
            lock_id = int(body.origin_key_id[:15], 16)
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
            existing = db.get(Incident, envelope.message_id)
            if existing:
                return receipt(existing, True)
        # Database-backed origin quota; signature identity is not verified human identity.
        recent = db.scalar(select(func.count()).select_from(Incident).where(
            Incident.received_at_ms >= now - 3600000,
            Incident.body["origin_key_id"].as_string() == body.origin_key_id))
        if recent >= 30:
            raise HTTPException(429, "Vượt giới hạn 30 SOS mới mỗi giờ cho một khóa thiết bị")
        row = Incident(message_id=envelope.message_id, incident_id=body.incident_id,
                       body=body.model_dump(), envelope=envelope.model_dump(), priority=body.priority,
                       created_at_ms=body.created_at_ms, received_at_ms=now, ai=suggest(body))
        db.add(row)
        db.add(AuditEvent(message_id=envelope.message_id, event="RECEIVED", details="drill gateway", at_ms=now))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.get(Incident, envelope.message_id)
            if existing:
                return receipt(existing, True)
            raise HTTPException(409, "Incident ID đã tồn tại; v0.2 chỉ hỗ trợ SOS_CREATED")
        return JSONResponse(receipt(row, False), status_code=201)

    @app.get("/api/v1/sos", dependencies=[Depends(require_admin)])
    def list_sos(limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0), db=Depends(session)):
        rows = db.scalars(select(Incident).order_by(Incident.priority, Incident.received_at_ms.desc(), Incident.message_id).offset(offset).limit(limit)).all()
        return {"items": [view(row) for row in rows], "total": db.scalar(select(func.count()).select_from(Incident))}

    @app.patch("/api/v1/sos/{message_id}", dependencies=[Depends(require_admin)])
    def change_status(message_id: str, data: StatusUpdate, db=Depends(session)):
        row = db.get(Incident, message_id)
        if not row:
            raise HTTPException(404, "Không tìm thấy SOS")
        allowed = {"NEW": {"VERIFIED"}, "VERIFIED": {"ASSIGNED"}, "ASSIGNED": {"RESOLVED"}, "RESOLVED": set()}
        if row.version != data.version:
            raise HTTPException(409, "Dữ liệu đã thay đổi; tải lại trước khi sửa")
        if data.status not in allowed[row.status]:
            raise HTTPException(422, "Chuyển trạng thái không hợp lệ")
        team = (data.assigned_team or "").strip() or row.assigned_team
        if data.status == "ASSIGNED" and not team:
            raise HTTPException(422, "Cần nhập đội được phân công")
        result = db.execute(update(Incident).where(Incident.message_id == message_id, Incident.version == data.version)
                            .values(status=data.status, assigned_team=team, version=data.version + 1)
                            .execution_options(synchronize_session=False))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Xung đột cập nhật")
        db.add(AuditEvent(message_id=message_id, event=data.status,
                         details=json.dumps({"team": team, "actor": "shared-demo-operator"}), at_ms=int(time.time() * 1000)))
        db.commit()
        db.expire_all()
        return view(db.get(Incident, message_id))

    @app.get("/api/v1/sos/{message_id}/events", dependencies=[Depends(require_admin)])
    def events(message_id: str, db=Depends(session)):
        rows = db.scalars(select(AuditEvent).where(AuditEvent.message_id == message_id).order_by(AuditEvent.id)).all()
        return [{"event": r.event, "details": r.details, "at_ms": r.at_ms} for r in rows]

    from .research_api import build_router
    app.include_router(build_router(session, require_admin, view))
    return app
