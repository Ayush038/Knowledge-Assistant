from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
load_dotenv()
from chat.chat_session_model import create_chat_session



chat_bp = Blueprint("chat", __name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client["KnowledgeAssistant"]
chat_sessions = db["chat_sessions"]


@chat_bp.route("/session", methods=["POST"])
@jwt_required()
def create_session():
    user_id = get_jwt_identity()
    data = request.json or {}

    title = data.get("title")

    session = create_chat_session(
        user_id=user_id,
        title=title
    )

    result = chat_sessions.insert_one(session)

    return jsonify({
        "success": True,
        "session_id": str(result.inserted_id)
    }), 201


@chat_bp.route("/history/<session_id>", methods=["GET"])
@jwt_required()
def get_chat_history(session_id):
    user_id = get_jwt_identity()

    session = chat_sessions.find_one({
        "_id": ObjectId(session_id),
        "user_id": ObjectId(user_id)
    })

    if not session:
        return jsonify({
            "success": False,
            "msg": "Chat session not found"
        }), 404

    messages_collection = db["messages"]

    msgs = list(
        messages_collection.find(
            {"session_id": ObjectId(session_id)},
            {"_id": 0}
        ).sort("created_at", 1)
    )

    for msg in msgs:
        msg["session_id"] = str(msg["session_id"])
        msg["user_id"] = str(msg["user_id"])

    return jsonify({
        "success": True,
        "session_id": session_id,
        "messages": msgs
    }), 200


@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_chat_sessions():
    user_id = get_jwt_identity()

    sessions = list(
        chat_sessions.find(
            {"user_id": ObjectId(user_id)},
            {"_id": 1, "title": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1)
    )

    for s in sessions:
        s["session_id"] = str(s["_id"])
        del s["_id"]

    return jsonify({
        "success": True,
        "sessions": sessions
    }), 200
