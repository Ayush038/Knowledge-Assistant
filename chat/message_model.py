from datetime import datetime
from bson import ObjectId

def create_message(session_id: str, user_id: str, role: str, content: str, sources=None):
    return {
        "session_id": ObjectId(session_id),
        "user_id": ObjectId(user_id),
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": datetime.utcnow()
    }