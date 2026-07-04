from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Table, Text
)
from sqlalchemy.orm import relationship
from app.core.database import Base

# Join table for Case and Complaint (many-to-many)
case_complaints = Table(
    "case_complaints",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("complaint_id", Integer, ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # citizen, officer, bank_analyst, telecom_analyst, admin
    jurisdiction_id = Column(Integer, ForeignKey("jurisdictions.id"), nullable=True)

    jurisdiction = relationship("Jurisdiction", back_populates="users")
    cases = relationship("Case", back_populates="officer")
    audit_logs = relationship("AuditLog", back_populates="user")

class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # The polygon_geom column will be added/handled as a raw Geometry in the database
    # In SQLAlchemy we can represent it as a string for input/output or handle it via raw queries

    users = relationship("User", back_populates="jurisdiction")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    reporter_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    text_content = Column(Text, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # PostGIS geometry column: location (POINT) will be managed via raw DDL and custom queries

    evidence_items = relationship("EvidenceItem", back_populates="complaint", cascade="all, delete-orphan")
    cases = relationship("Case", secondary=case_complaints, back_populates="complaints")

class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # transcript, audio, image, document, transaction
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    sha256_hash = Column(String, nullable=False)
    previous_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="evidence_items")

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="Open")  # Open, Under Investigation, Resolved, Closed
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    officer = relationship("User", back_populates="cases")
    complaints = relationship("Complaint", secondary=case_complaints, back_populates="cases")

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # phone, account, device
    value = Column(String, nullable=False)  # the actual value (e.g. phone number, bank account)
    value_hash = Column(String, unique=True, index=True, nullable=False)  # hashed value for privacy
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class EntityLink(Base):
    __tablename__ = "entity_links"

    id = Column(Integer, primary_key=True, index=True)
    entity_a_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    entity_b_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String, nullable=False)  # shared_phone, transaction, shared_device
    weight = Column(Float, default=1.0)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_account = Column(String, nullable=False)
    receiver_account = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CounterfeitScan(Base):
    __tablename__ = "counterfeit_scans"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    result_verdict = Column(String, nullable=False)  # Genuine, Counterfeit, Suspect
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    caller_number = Column(String, nullable=False)
    callee_number = Column(String, nullable=False)
    transcript = Column(Text, nullable=False)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="Medium")
    status = Column(String, default="Unread")  # Unread, Read, Dismissed
    target_role = Column(String, nullable=False)  # citizen, officer, bank_analyst, telecom_analyst, admin
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)  # nlp_classifier, counterfeit_vision, speech_service, graph_service
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    fpr = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)
