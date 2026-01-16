import os
import requests
import tempfile
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

import cloudinary
import cloudinary.uploader

from documents.model import create_document
from documents.chunk_model import document_chunk
from documents.chunk import chunk_text
from documents.text_extractor import extract_text
from embeddings.retriever import retrieve_chunks
from llm.generator import generate_answer
from chat.chat_session_model import create_chat_session
from chat.message_model import create_message
from chat.utils import get_recent_messages, format_chat_history
from documents.usage_log_model import create_llm_usage_log
import re


document_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"txt", "pdf"}


client = MongoClient(os.getenv("MONGO_URI"))
db = client["KnowledgeAssistant"]
documents_collection = db["documents"]
chunks_collection = db["document_chunks"]
chat_sessions = db["chat_sessions"]
messages = db["messages"]
llm_usage_logs = db["llm_usage_logs"]
user_usage = db["user_usage"]


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
    original_filename = file.filename
    file_type = original_filename.rsplit(".", 1)[1].lower()


    upload_result = cloudinary.uploader.upload(
        file,
        resource_type="raw",
        folder="knowledge_assistant"
    )

    cloudinary_url = upload_result["secure_url"]
    public_id = upload_result["public_id"]

    response = requests.get(cloudinary_url)
    if response.status_code != 200:
        return jsonify({"success": False, "msg": "Failed to download file"}), 500

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(response.content)
        temp_path = tmp.name

    extracted_text = extract_text(temp_path, file_type)

    document = create_document(
        filename=public_id,
        original_filename=original_filename,
        file_type=file_type,
        uploaded_by=user_id
    )

    document.update({
        "cloudinary_url": cloudinary_url,
        "status": "processed"
    })

    doc_result = documents_collection.insert_one(document)
    document_id = doc_result.inserted_id

    chunks = chunk_text(extracted_text)

    for index, chunk_text_data in enumerate(chunks):
        chunks_collection.insert_one(
            document_chunk(
                document_id=document_id,
                chunk_index=index,
                text=chunk_text_data
            )
        )

    documents_collection.update_one(
        {"_id": document_id},
        {
            "$set": {
                "chunk_count": len(chunks),
                "status": "processed"
            }
        }
    )

    return jsonify({
        "success": True,
        "msg": "Document uploaded successfully",
        "document_id": str(document_id),
        "file_url": cloudinary_url
    }), 201


@document_bp.route("/list", methods=["GET"])
@jwt_required()
def list_documents():
    claims = get_jwt()
    role = claims.get("role")
    user_id = get_jwt_identity()

    query = {"is_active": True}
    if role != "admin":
        query["uploaded_by"] = ObjectId(user_id)

    documents = list(documents_collection.find(query, {"_id": 0}))
    return jsonify({"success": True, "documents": documents}), 200


@document_bp.route("/search", methods=["POST"])
@jwt_required()
def search_query():
    data = request.json

    if not data or "query" not in data:
        return jsonify({"success": False, "msg": "Query is required"}), 400

    query = data["query"]
    top_k = data.get("top_k", 5)

    claims = get_jwt()
    role = claims.get("role")
    user_id = get_jwt_identity()

    results = retrieve_chunks(
        query,
        top_k=top_k,
        user_id=user_id,
        is_admin=(role == "admin")
    )

    return jsonify({"success": True, "results": results}), 200


@document_bp.route("/ask", methods=["POST"])
@jwt_required()
def ask_question():
    data = request.json

    if not data or "query" not in data:
        return jsonify({"success": False, "msg": "Query is required"}), 400

    user_id = get_jwt_identity()
    query = data["query"]
    top_k = data.get("top_k", 1)
    session_id = data.get("session_id")

    if not session_id:
        session = create_chat_session(user_id=user_id)
        result = chat_sessions.insert_one(session)
        session_id = str(result.inserted_id)

    if is_small_talk(query):
        answer = "Hi there. Ask me something based on your uploaded documents and I’ll help."

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
    messages.insert_one(
        create_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=query
        )
    )
    chat_history = ""
    recent_messages = get_recent_messages(
        messages_collection=messages,
        session_id=session_id,
        limit=6
    )
    chat_history = format_chat_history(recent_messages)

    claims = get_jwt()
    role = claims.get("role")

    retrieved_chunks = retrieve_chunks(
        query,
        top_k=top_k,
        user_id=user_id,
        is_admin=(role == "admin")
    )

    answer_payload = generate_answer(
        query=query,
        retrieved_chunks=retrieved_chunks,
        chat_history=chat_history
    )

    usage = answer_payload.get("usage")

    if usage:
        INPUT_TOKEN_PRICE = 0.0001 / 1000
        OUTPUT_TOKEN_PRICE = 0.0002 / 1000

        cost = (
            usage["input_tokens"] * INPUT_TOKEN_PRICE +
            usage["output_tokens"] * OUTPUT_TOKEN_PRICE
        )
        log = create_llm_usage_log(
            user_id=user_id,
            session_id=session_id,
            model=usage["model"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            total_tokens=usage["total_tokens"],
            cost=cost
        )

        try:
            llm_usage_logs.insert_one(log)

            user_usage.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$inc": {
                        "total_tokens": usage["total_tokens"],
                        "total_cost": round(cost, 6)
                    },
                    "$set": {
                        "last_used": datetime.utcnow()
                    }
                },
                upsert=True
            )
        except Exception as e:
            print("LLM usage logging failed:", e)

    messages.insert_one(
        create_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=answer_payload["answer"],
            sources=answer_payload["sources"]
        )
    )

    chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "answer": answer_payload["answer"],
        "sources": answer_payload["sources"]
    }), 200
