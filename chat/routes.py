from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
from logger import get_logger
from services.chat.session_service import create_new_chat_session
from services.chat.history_service import fetch_chat_history
from services.chat.list_service import list_user_sessions

logger = get_logger(__name__)

chat_bp = Blueprint("chat", __name__)

chat_sessions = db["chat_sessions"]


@chat_bp.route("/session", methods=["POST"])
@jwt_required()
def create_session():
    user_id = get_jwt_identity()
    data = request.json or {}

    title = data.get("title")

    result = create_new_chat_session(user_id=user_id, title=title)

    if not result:
        return jsonify({
            "success": False,
            "msg": "Cannot create new chat until a message is sent in the last chat"
        }), 400

    return jsonify({
        "success": True,
        **result
    }), 201


@chat_bp.route("/history/<session_id>", methods=["GET"])
@jwt_required()
def get_chat_history(session_id):
    user_id = get_jwt_identity()

    try:
        result = fetch_chat_history(user_id=user_id, session_id=session_id)
    except Exception:
        logger.exception("Failed to fetch chat history")
        return jsonify({"success": False, "msg": "Failed to fetch history"}), 500

    if not result:
        return jsonify({"success": False, "msg": "Chat session not found"}), 404

    return jsonify({"success": True, **result}), 200



@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_chat_sessions():
    user_id = get_jwt_identity()

    try:
        result = list_user_sessions(user_id)
    except Exception:
        logger.exception("Failed to fetch chat sessions")
        return jsonify({"success": False, "msg": "Failed to fetch sessions"}), 500

    return jsonify({"success": True, **result}), 200