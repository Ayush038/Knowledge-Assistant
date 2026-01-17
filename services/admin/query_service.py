from bson import ObjectId
from db import db

messages_collection = db["messages"]
users_collection = db["users"]


def fetch_user_queries(*, user_id=None):
    query_filter = {"role": "user"}

    if user_id and ObjectId.is_valid(user_id):
        query_filter["user_id"] = ObjectId(user_id)

    queries = list(
        messages_collection.find(
            query_filter,
            {
                "_id": 0,
                "user_id": 1,
                "session_id": 1,
                "content": 1,
                "created_at": 1
            }
        ).sort("created_at", -1)
    )

    user_ids = [
        ObjectId(q["user_id"])
        for q in queries
        if ObjectId.is_valid(str(q["user_id"]))
    ]

    users = {
        str(user["_id"]): user["username"]
        for user in users_collection.find(
            {"_id": {"$in": user_ids}},
            {"username": 1}
        )
    }

    for q in queries:
        uid = str(q["user_id"])
        q["user"] = users.get(uid, "Unknown User")
        q["session_id"] = str(q["session_id"])
        del q["user_id"]

    return {"queries": queries}
