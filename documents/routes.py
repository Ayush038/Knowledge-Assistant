from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from chat.chat_session_model import create_chat_session
from chat.message_model import create_message
from db import db
import re
from logger import get_logger
from services.documents.upload_service import upload_document
from services.documents.ask_service import handle_ask_query
from services.documents.search_service import handle_search_query
from services.documents.list_service import get_user_documents
logger = get_logger(__name__)


document_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"txt", "pdf"}


chat_sessions = db["chat_sessions"]
messages = db["messages"]


SMALL_TALK_PATTERNS = [
    r"^hi$",
    r"^hello$",
    r"^hey$",
    r"^how are you\??$",
    r"^thanks?$",
    r"^thank you$",
    r"^ok$",
    r"^okay$",
    r"^cool$"
]

def is_small_talk(query: str) -> bool:
    q = query.strip().lower()
    return any(re.match(p, q) for p in SMALL_TALK_PATTERNS)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@document_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_doc():
    if "file" not in request.files:
        return jsonify({"success": False, "msg": "No file present"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "msg": "Empty File Name"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "msg": "Invalid Extension"}), 400

    user_id = get_jwt_identity()

    try:
        result = upload_document(file, user_id)
    except Exception as e:
        logger.exception("Document upload failed")
        return jsonify({
            "success": False,
            "msg": "Document upload failed"
        }), 500

    return jsonify({
        "success": True,
        "msg": "Document uploaded successfully",
        **result
    }), 201


@document_bp.route("/list", methods=["GET"])
@jwt_required()
def list_documents():
    user_id = get_jwt_identity()
    role = get_jwt().get("role")

    try:
        result = get_user_documents(user_id=user_id, role=role)
    except Exception:
        logger.exception("Failed to fetch documents")
        return jsonify({"success": False, "msg": "Failed to fetch documents"}), 500

    return jsonify({"success": True, **result}), 200


@document_bp.route("/search", methods=["POST"])
@jwt_required()
def search_query():
    data = request.json

    if not data or "query" not in data:
        return jsonify({"success": False, "msg": "Query is required"}), 400

    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    try:
        result = handle_search_query(
            query=data["query"],
            top_k=data.get("top_k", 5),
            user_id=user_id,
            role=role
        )
    except Exception:
        logger.exception("Search failed")
        return jsonify({"success": False, "msg": "Search failed"}), 500

    return jsonify({"success": True, **result}), 200


@document_bp.route("/ask", methods=["POST"])
@jwt_required()
def ask_question():
    data = request.json

    if not data or "query" not in data:
        return jsonify({"success": False, "msg": "Query is required"}), 400

    user_id = get_jwt_identity()
    query = data["query"]
    top_k = data.get("top_k", 3)
    session_id = data.get("session_id")

    claims = get_jwt()
    role = claims.get("role")

    if is_small_talk(query):
        answer = "Hi there. Ask me something based on your uploaded documents and I’ll help."

        if not session_id:
            session = create_chat_session(user_id=user_id)
            result = chat_sessions.insert_one(session)
            session_id = str(result.inserted_id)

        messages.insert_one(
            create_message(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=answer,
                sources=[]
            )
        )

        return jsonify({
            "success": True,
            "session_id": session_id,
            "answer": answer,
            "sources": []
        }), 200

    try:
        result = handle_ask_query(
            user_id=user_id,
            query=query,
            top_k=top_k,
            session_id=session_id,
            role=role
        )
    except Exception:
        logger.exception("Ask query failed")
        return jsonify({
            "success": False,
            "msg": "Failed to process query"
        }), 500

    return jsonify({
        "success": True,
        **result
    }), 200