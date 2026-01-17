from bson import ObjectId
from chat.chat_session_model import create_chat_session
from db import db

chat_sessions = db["chat_sessions"]
messages = db["messages"]


def can_create_new_session(user_id):
    last_session = chat_sessions.find_one(
        {"user_id": ObjectId(user_id)},
        sort=[("created_at", -1)]
    )

    if not last_session:
        return True

    has_user_messages = messages.count_documents({
        "session_id": last_session["_id"],
        "role": "user"
    }) > 0

    return has_user_messages


def create_new_chat_session(user_id, title=None):
    if not can_create_new_session(user_id):
        return None

    session = create_chat_session(user_id=user_id, title=title)
    result = chat_sessions.insert_one(session)

    return {"session_id": str(result.inserted_id)}
