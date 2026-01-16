from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

admin_bp = Blueprint("admin", __name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client["KnowledgeAssistant"]

documents_collection = db["documents"]
messages_collection = db["messages"]
chat_sessions_collection = db["chat_sessions"]
users_collection = db["users"]
llm_usage_logs = db["llm_usage_logs"]
user_usage = db["user_usage"]


def require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"



@admin_bp.route("/documents", methods=["GET"])
@jwt_required()
def list_all_documents():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    documents = list(
        documents_collection.find(
            {},
            {
                "_id": 1,
                "original_filename": 1,
                "uploaded_by": 1,
                "uploaded_at": 1,   # FIXED
                "chunk_count": 1,
                "status": 1,
                "is_active": 1
            }
        )
    )
    uploader_ids = [
        ObjectId(doc["uploaded_by"])
        for doc in documents
        if ObjectId.is_valid(doc["uploaded_by"])
    ]

    users = {
        str(user["_id"]): user["username"]
        for user in users_collection.find(
            {"_id": {"$in": uploader_ids}},
            {"username": 1}
        )
    }

    for doc in documents:
        doc["_id"] = str(doc["_id"])

        uploader_id = doc["uploaded_by"]
        doc["uploaded_by"] = users.get(uploader_id, "Unknown User")

        doc["created_at"] = doc.pop("uploaded_at", None)

    return jsonify({"success": True, "documents": documents}), 200


@admin_bp.route("/documents/<document_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_document(document_id):
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    document = documents_collection.find_one({"_id": ObjectId(document_id)})

    if not document:
        return jsonify({"success": False, "msg": "Document not found"}), 404

    new_status = not document.get("is_active", True)

    documents_collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
    )

    return jsonify({
        "success": True,
        "document_id": document_id,
        "is_active": new_status
    }), 200



@admin_bp.route("/queries", methods=["GET"])
@jwt_required()
def list_user_queries():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    user_id = request.args.get("user_id")

    query_filter = {"role": "user"}
    if user_id:
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

    return jsonify({"success": True, "queries": queries}), 200



@admin_bp.route("/conversations", methods=["GET"])
@jwt_required()
def admin_conversations():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 1))
    user_id = request.args.get("user_id")

    session_filter = {}
    if user_id and ObjectId.is_valid(user_id):
        session_filter["user_id"] = ObjectId(user_id)

    skip = (page - 1) * limit

    sessions = list(
        chat_sessions_collection.find(
            session_filter
        )
        .sort("updated_at", -1)
        .skip(skip)
        .limit(limit)
    )

    if not sessions:
        return jsonify({"success": True, "sessions": [], "total": 0}), 200

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

    return jsonify({
        "success": True,
        "sessions": response_sessions,
        "total": total_sessions,
        "page": page
    }), 200


@admin_bp.route("/usage", methods=["GET"])
@jwt_required()
def usage_stats():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    user_id = request.args.get("user_id")

    user_filter = {}
    if user_id:
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

    return jsonify({"success": True, "stats": stats}), 200

@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    users = list(
        users_collection.find(
            {"is_active": True},
            {"_id": 1, "username": 1}
        )
    )

    for u in users:
        u["_id"] = str(u["_id"])

    return jsonify({
        "success": True,
        "users": users
    }), 200



@admin_bp.route("/llm-usage/summary", methods=["GET"])
@jwt_required()
def llm_usage_summary():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

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

    return jsonify({
        "success": True,
        "summary": {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "active_users": active_users
        }
    }), 200


@admin_bp.route("/llm-usage/users", methods=["GET"])
@jwt_required()
def llm_usage_by_user():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

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

    return jsonify({
        "success": True,
        "users": result
    }), 200

