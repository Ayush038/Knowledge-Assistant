from bson import ObjectId
from db import db

chat_sessions = db["chat_sessions"]


def list_user_sessions(user_id):
    sessions = list(
        chat_sessions.find(
            {"user_id": ObjectId(user_id)},
            {"_id": 1, "title": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1)
    )

    for s in sessions:
        s["session_id"] = str(s["_id"])
        del s["_id"]

    return {"sessions": sessions}
