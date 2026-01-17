from datetime import datetime
from bson import ObjectId
from db import db


chat_sessions = db["chat_sessions"]


def create_message(session_id: str, user_id: str, role: str, content: str, sources=None):
    message = {
        "session_id": ObjectId(session_id),
        "user_id": ObjectId(user_id),
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": datetime.utcnow()
    }

    if role == "user":
        session = chat_sessions.find_one({"_id": ObjectId(session_id)})

        if session and session.get("title") == "New Chat":
            chat_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "title": content[:50],
                        "updated_at": datetime.utcnow()
                    }
                }
            )

    return message
