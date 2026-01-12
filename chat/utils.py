from bson import ObjectId

def get_recent_messages(messages_collection, session_id, limit=6):
    return list(
        messages_collection.find(
            {"session_id": ObjectId(session_id)},
            {"_id": 0, "role": 1, "content": 1}
        )
        .sort("created_at", -1)
        .limit(limit)
    )[::-1]


def format_chat_history(history):
    lines = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)