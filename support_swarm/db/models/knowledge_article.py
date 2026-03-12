from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from support_swarm.db.models.base import Base


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @classmethod
    def search_by_embedding(
        cls, session: Session, embedding: list[float], limit: int = 3
    ) -> list[KnowledgeArticle]:
        """Return the closest articles by cosine distance to the given embedding."""
        stmt = (
            select(cls)
            .where(cls.embedding.isnot(None))
            .order_by(cls.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())
