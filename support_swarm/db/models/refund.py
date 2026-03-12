from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from support_swarm.db.models.base import Base


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="refunds")

    @classmethod
    def create(
        cls,
        session: Session,
        order_id: str,
        amount: Decimal,
        reason: str,
        status: str = "processed",
    ) -> Refund:
        """Create and flush a new refund record."""
        refund = cls(
            id=uuid.uuid4(),
            order_id=order_id,
            amount=amount,
            reason=reason,
            status=status,
            processed_at=datetime.now(timezone.utc)
            if status in ("processed", "approved")
            else None,
        )
        session.add(refund)
        session.flush()
        return refund

    @classmethod
    def get_by_order_id(cls, session: Session, order_id: str) -> list[Refund]:
        """Return all refunds for a given order."""
        stmt = select(cls).where(cls.order_id == order_id)
        return list(session.execute(stmt).scalars().all())

    @classmethod
    def get_by_customer_orders(
        cls, session: Session, order_ids: list[str]
    ) -> list[Refund]:
        """Return all refunds across multiple orders."""
        if not order_ids:
            return []
        stmt = select(cls).where(cls.order_id.in_(order_ids))
        return list(session.execute(stmt).scalars().all())
