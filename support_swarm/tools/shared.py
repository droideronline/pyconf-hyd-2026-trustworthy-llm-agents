import json

from support_swarm.db.engine import get_session
from support_swarm.db.models import KnowledgeArticle
from support_swarm.model_client import get_embedding_client
from support_swarm.tools.registry import register_tool


@register_tool
def search_knowledge_base(query: str) -> str:
    """Search policy documents and FAQ articles using semantic search.

    Returns the most relevant policy documents matching the query.
    Use this to find return policies, refund policies, shipping policies,
    warranty terms, and escalation guidelines.

    Args:
        query: A natural-language search query describing what policy
               information you need.
    """
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
