from datetime import datetime
from bson import ObjectId


def create_llm_usage_log(
    user_id,
    session_id,
    model,
    input_tokens,
    output_tokens,
    total_tokens,
    cost,
    endpoint="/ask"
):
    return {
        "user_id": ObjectId(user_id),
        "session_id": ObjectId(session_id),
        "endpoint": endpoint,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": round(cost, 6),
        "created_at": datetime.utcnow()
    }
