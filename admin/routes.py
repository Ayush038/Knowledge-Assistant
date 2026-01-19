from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from db import db
from services.admin.document_service import fetch_all_documents,toggle_document_status
from services.admin.query_service import fetch_user_queries
from services.admin.conversation_service import fetch_admin_conversations
from services.admin.usage_service import (
    fetch_usage_stats,
    fetch_active_users,
    fetch_llm_usage_summary,
    fetch_llm_usage_by_user
)


admin_bp = Blueprint("admin", __name__)


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

    result = fetch_all_documents()
    return jsonify({"success": True, **result}), 200


@admin_bp.route("/documents/<document_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_document(document_id):
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    result = toggle_document_status(document_id)

    if not result:
        return jsonify({"success": False, "msg": "Document not found"}), 404

    return jsonify({"success": True, **result}), 200



@admin_bp.route("/queries", methods=["GET"])
@jwt_required()
def list_user_queries():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    user_id = request.args.get("user_id")

    result = fetch_user_queries(user_id=user_id)

    return jsonify({"success": True, **result}), 200



@admin_bp.route("/conversations", methods=["GET"])
@jwt_required()
def admin_conversations():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    user_id = request.args.get("user_id")

    try:
        result = fetch_admin_conversations(
            page=page,
            limit=limit,
            user_id=user_id
        )
    except Exception:
        return jsonify({"success": False, "msg": "Failed to fetch conversations"}), 500

    return jsonify({"success": True, **result}), 200


@admin_bp.route("/usage", methods=["GET"])
@jwt_required()
def usage_stats():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    user_id = request.args.get("user_id")

    result = fetch_usage_stats(user_id=user_id)
    return jsonify({"success": True, **result}), 200

@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    result = fetch_active_users()
    return jsonify({"success": True, **result}), 200



@admin_bp.route("/llm-usage/summary", methods=["GET"])
@jwt_required()
def llm_usage_summary():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    result = fetch_llm_usage_summary()
    return jsonify({"success": True, **result}), 200


@admin_bp.route("/llm-usage/users", methods=["GET"])
@jwt_required()
def llm_usage_by_user():
    if not require_admin():
        return jsonify({"success": False, "msg": "Admin access required"}), 403

    result = fetch_llm_usage_by_user()
    return jsonify({"success": True, **result}), 200