from bson import ObjectId
from db import db

chat_sessions_collection = db["chat_sessions"]
messages_collection = db["messages"]
users_collection = db["users"]


def fetch_admin_conversations(*, page=1, limit=10, user_id=None):
    session_filter = {}

    if user_id and ObjectId.is_valid(user_id):
        session_filter["user_id"] = ObjectId(user_id)

    skip = (page - 1) * limit

    sessions = list(
        chat_sessions_collection.find(session_filter)
        .sort("updated_at", -1)
        .skip(skip)
        .limit(limit)
    )

    if not sessions:
        return {"sessions": [], "total": 0, "page": page}

    user_ids = list({s["user_id"] for s in sessions})

    users = {
        str(u["_id"]): u["username"]
        for u in users_collection.find(
            {"_id": {"$in": user_ids}},
            {"username": 1}
        )
    }

    response_sessions = []

    for session in sessions:
        messages = list(
            messages_collection.find(
                {"session_id": session["_id"]},
                {"_id": 0, "role": 1, "content": 1, "created_at": 1}
            ).sort("created_at", 1)
        )

        response_sessions.append({
            "session_id": str(session["_id"]),
            "username": users.get(str(session["user_id"]), "Unknown User"),
            "created_at": session["created_at"],
            "messages": messages
        })

    total_sessions = chat_sessions_collection.count_documents(session_filter)

    return {
        "sessions": response_sessions,
        "total": total_sessions,
        "page": page
    }
