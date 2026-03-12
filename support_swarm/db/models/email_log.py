from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from support_swarm.db.models.base import Base


class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @classmethod
    def create(
        cls, session: Session, customer_email: str, subject: str, body: str
    ) -> EmailLog:
        """Create and flush a new email log record."""
        email = cls(
            id=uuid.uuid4(),
            customer_email=customer_email,
            subject=subject,
            body=body,
        )
        session.add(email)
        session.flush()
        return email
