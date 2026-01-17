from bson import ObjectId
from db import db

chat_sessions = db["chat_sessions"]
messages_collection = db["messages"]


def fetch_chat_history(*, user_id, session_id):
    session = chat_sessions.find_one({
        "_id": ObjectId(session_id),
        "user_id": ObjectId(user_id)
    })

    if not session:
        return None

    msgs = list(
        messages_collection.find(
            {"session_id": ObjectId(session_id)},
            {"_id": 0}
        ).sort("created_at", 1)
    )

    for msg in msgs:
        msg["session_id"] = str(msg["session_id"])
        msg["user_id"] = str(msg["user_id"])

    return {
        "session_id": session_id,
        "messages": msgs
    }
