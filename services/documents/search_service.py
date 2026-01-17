from flask_jwt_extended import get_jwt
from logger import get_logger
from embeddings.retriever import retrieve_chunks

logger = get_logger(__name__)


def handle_search_query(*, query, top_k, user_id, role):
    results = retrieve_chunks(
        query,
        top_k=top_k,
        user_id=user_id,
        is_admin=(role == "admin")
    )

    return {"results": results}
