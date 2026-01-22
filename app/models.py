from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    note = Column(Text, nullable=False)
    campaign = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    max_uses = Column(Integer, nullable=True)
    is_disabled = Column(Boolean, nullable=False, default=False)

    visits = relationship("Visit", back_populates="invite")


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    invite_id = Column(Integer, ForeignKey("invites.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip = Column(String(64), nullable=False)
    user_agent = Column(Text, nullable=False)
    day_bucket = Column(String(10), nullable=False, index=True)

    invite = relationship("Invite", back_populates="visits")


class VisitEvent(Base):
    __tablename__ = "visit_events"

    id = Column(Integer, primary_key=True)
    invite_id = Column(Integer, ForeignKey("invites.id"), nullable=True)
    token = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip = Column(String(64), nullable=False)
    user_agent = Column(Text, nullable=False)
    result = Column(String(32), nullable=False)

    invite = relationship("Invite")
