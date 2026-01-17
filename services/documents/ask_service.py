from bson import ObjectId
from datetime import datetime
from logger import get_logger

from chat.chat_session_model import create_chat_session
from chat.message_model import create_message
from chat.utils import get_recent_messages, format_chat_history
from embeddings.retriever import retrieve_chunks
from llm.generator import generate_answer
from documents.usage_log_model import create_llm_usage_log
from db import db

logger = get_logger(__name__)

chat_sessions = db["chat_sessions"]
messages = db["messages"]
llm_usage_logs = db["llm_usage_logs"]
user_usage = db["user_usage"]


def handle_ask_query(
    *,
    user_id,
    query,
    top_k,
    session_id,
    role
):
    # Create session if missing
    if not session_id:
        session = create_chat_session(user_id=user_id)
        result = chat_sessions.insert_one(session)
        session_id = str(result.inserted_id)

    # Store user message
    messages.insert_one(
        create_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=query
        )
    )

    # Build chat history
    recent_messages = get_recent_messages(
        messages_collection=messages,
        session_id=session_id,
        limit=6
    )
    chat_history = format_chat_history(recent_messages)

    # Retrieve document chunks
    retrieved_chunks = retrieve_chunks(
        query,
        top_k=top_k,
        user_id=user_id,
        is_admin=(role == "admin")
    )

    # Generate answer
    answer_payload = generate_answer(
        query=query,
        retrieved_chunks=retrieved_chunks,
        chat_history=chat_history
    )

    usage = answer_payload.get("usage")

    # Log usage if present
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
            logger.error("LLM usage logging failed", exc_info=e)

    # Store assistant message
    messages.insert_one(
        create_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=answer_payload["answer"],
            sources=answer_payload["sources"]
        )
    )

    # Update session timestamp
    chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )

    return {
        "session_id": session_id,
        "answer": answer_payload["answer"],
        "sources": answer_payload["sources"]
    }
