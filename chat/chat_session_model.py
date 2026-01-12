from datetime import datetime
from bson import ObjectId

def create_chat_session(user_id: str, title: str = None):
    return {
        "user_id": ObjectId(user_id),
        "title": title or "New Chat",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }