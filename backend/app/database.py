from sqlalchemy import JSON, BigInteger, Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Incident(Base):
    __tablename__ = "incidents"
    message_id = Column(String(64), primary_key=True)
    incident_id = Column(String(36), unique=True, nullable=False)
    body = Column(JSON, nullable=False)
    envelope = Column(JSON, nullable=False)
    priority = Column(Integer, nullable=False, index=True)
    status = Column(String(24), default="NEW", nullable=False, index=True)
    assigned_team = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at_ms = Column(BigInteger, nullable=False)
    received_at_ms = Column(BigInteger, nullable=False)
    ai = Column(JSON, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    message_id = Column(String(64), nullable=False, index=True)
    event = Column(String(32), nullable=False)
    details = Column(Text, nullable=False)
    at_ms = Column(BigInteger, nullable=False)


def connect_database(url):
    kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=kwargs, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
