from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, JSON, func, Boolean
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # INSERT, UPDATE, DELETE
    user_id: Mapped[str] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    old_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    version_index: Mapped[int] = mapped_column(Integer, default=1)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=True)

class AuditedModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, **kwargs):
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        super().__init__(**kwargs)

class TranslationJob(AuditedModel):
    __tablename__ = 'translation_jobs'

    study_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False) # PENDING, COMPLETED, FAILED
    odm_payload: Mapped[str] = mapped_column(String, nullable=True)
    openrosa_payload: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

