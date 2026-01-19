from bson import ObjectId
from db import db

documents_collection = db["documents"]
messages_collection = db["messages"]
chat_sessions_collection = db["chat_sessions"]
users_collection = db["users"]
llm_usage_logs = db["llm_usage_logs"]
user_usage = db["user_usage"]


def fetch_usage_stats(user_id=None):
    user_filter = {}

    if user_id and ObjectId.is_valid(user_id):
        user_filter["user_id"] = ObjectId(user_id)

    stats = {
        "total_users": users_collection.count_documents({}) if not user_id else 1,
        "total_documents": documents_collection.count_documents({}),
        "total_chat_sessions": chat_sessions_collection.count_documents(user_filter),
        "total_user_queries": messages_collection.count_documents(
            {**user_filter, "role": "user"}
        ),
        "total_ai_responses": messages_collection.count_documents(
            {**user_filter, "role": "assistant"}
        )
    }

    return {"stats": stats}


def fetch_active_users():
    users = list(
        users_collection.find(
            {"is_active": True},
            {"_id": 1, "username": 1}
        )
    )

    for u in users:
        u["_id"] = str(u["_id"])

    return {"users": users}


def fetch_llm_usage_summary():
    total_requests = llm_usage_logs.count_documents({})

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_tokens": {"$sum": "$total_tokens"},
                "total_cost": {"$sum": "$cost"}
            }
        }
    ]

    agg_result = list(llm_usage_logs.aggregate(pipeline))

    if agg_result:
        total_tokens = agg_result[0]["total_tokens"]
        total_cost = round(agg_result[0]["total_cost"], 6)
    else:
        total_tokens = 0
        total_cost = 0.0

    active_users = user_usage.count_documents({})

    return {
        "summary": {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "active_users": active_users
        }
    }


def fetch_llm_usage_by_user():
    users = {
        str(u["_id"]): u["username"]
        for u in users_collection.find({}, {"username": 1})
    }

    usage = list(user_usage.find({}))

    result = []

    for u in usage:
        uid = str(u["user_id"])
        result.append({
            "user_id": uid,
            "username": users.get(uid, "Unknown User"),
            "total_tokens": u.get("total_tokens", 0),
            "total_cost": u.get("total_cost", 0),
            "last_used": u.get("last_used")
        })

    return {"users": result}
