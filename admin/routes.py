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
                "chunk_count": 1,
                "status": 1,
                "is_active": 1,
                "created_at": 1
            }
        )
    )

    for doc in documents:
        doc["_id"] = str(doc["_id"])
        doc["uploaded_by"] = str(doc["uploaded_by"])

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

    for q in queries:
        q["user_id"] = str(q["user_id"])
        q["session_id"] = str(q["session_id"])

    return jsonify({"success": True, "queries": queries}), 200



@admin_bp.route("/conversations", methods=["GET"])
@jwt_required()
def admin_conversations():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    user_id = request.args.get("user_id")

    session_filter = {}
    if user_id:
        session_filter["user_id"] = ObjectId(user_id)

    sessions = list(
        chat_sessions_collection.find(
            session_filter,
            {"_id": 1, "user_id": 1, "title": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1)
    )

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
            "user_id": str(session["user_id"]),
            "title": session.get("title"),
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "messages": messages
        })

    return jsonify({
        "success": True,
        "sessions": response_sessions
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
