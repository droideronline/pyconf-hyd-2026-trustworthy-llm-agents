import json

from pydantic import BaseModel, Field

from support_swarm.db.engine import get_session
from support_swarm.db.models import KnowledgeArticle
from support_swarm.model_client import get_embedding_client
from support_swarm.tools.registry import register_tool


class SearchKnowledgeBaseInput(BaseModel):
    """Input for searching the knowledge base."""

    query: str = Field(
        description="Natural-language search query for policy documents and FAQs"
    )


@register_tool(args_schema=SearchKnowledgeBaseInput)
def search_knowledge_base(query: str) -> str:
    """Search policy documents and FAQ articles using semantic search."""
    with get_session() as session:
        query_embedding = get_embedding_client().embed_query(query)
        articles = KnowledgeArticle.search_by_embedding(session, query_embedding)
        return json.dumps(
            [
                {
                    "article_id": str(a.id),
                    "title": a.title,
                    "category": a.category,
                    "content": a.content,
                }
                for a in articles
            ],
            indent=2,
        )
