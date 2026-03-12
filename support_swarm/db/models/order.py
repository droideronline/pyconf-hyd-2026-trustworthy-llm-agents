from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, joinedload, mapped_column, relationship

from support_swarm.db.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. ORD-1001
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped[Customer] = relationship(back_populates="orders")
    refunds: Mapped[list[Refund]] = relationship(back_populates="order")

    @classmethod
    def get_by_id(cls, session: Session, order_id: str) -> Order | None:
        """Fetch a single order by its ID, eagerly loading the customer."""
        stmt = select(cls).options(joinedload(cls.customer)).where(cls.id == order_id)
        return session.execute(stmt).scalar_one_or_none()

    @classmethod
    def get_by_customer_email(cls, session: Session, email: str) -> list[Order]:
        """Return all orders for a customer identified by email, newest first."""
        from support_swarm.db.models.customer import Customer

        stmt = (
            select(cls)
            .join(Customer)
            .options(joinedload(cls.customer))
            .where(Customer.email == email)
            .order_by(cls.created_at.desc())
        )
        return list(session.execute(stmt).scalars().unique().all())
