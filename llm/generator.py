import os
import time
from groq import Groq
from logger import get_logger
logger = get_logger(__name__)


client = Groq(api_key=os.getenv("LLM_API"))

MAX_CHARS_PER_CHUNK = 1000
MAX_TOTAL_CONTEXT_CHARS = 5000
MAX_TOKENS_TO_GENERATE = 256


def _trim_text(text: str, max_chars: int) -> str:
    return text[:max_chars] if text else ""


def generate_answer(query, retrieved_chunks, chat_history=""):
    if not retrieved_chunks:
        return {
            "answer": "I do not know.",
            "sources": []
        }

    # Build controlled context
    context_parts = []
    total_chars = 0
    

    for c in retrieved_chunks:
        trimmed = _trim_text(c["text"], MAX_CHARS_PER_CHUNK)
        block = f"[Chunk {c['chunk_index']}]\n{trimmed}"

        if total_chars + len(block) > MAX_TOTAL_CONTEXT_CHARS:
            break

        context_parts.append(block)
        total_chars += len(block)

    context = "\n\n".join(context_parts)

    prompt = f"""
    You are a helpful assistant that answers questions ONLY using the provided document context.
    Conversation history is provided ONLY to understand the question, not as a source of facts.
    If the answer is not in the document context, say "I do not know".

    CONVERSATION HISTORY:
    {chat_history if chat_history else "None"}

    DOCUMENT CONTEXT:
    {context}

    QUESTION:
    {query}

    INSTRUCTIONS:
    - Answer concisely
    - Do not add external knowledge
    - Cite sources using chunk_index
    """

    start = time.time()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=MAX_TOKENS_TO_GENERATE,
    )
    usage = response.usage

    logger.info("LLM inference time: %.2f seconds", time.time() - start)

    return {
        "answer": response.choices[0].message.content.strip(),
        "sources": [
            {
                "document_id": c["document_id"],
                "chunk_index": c["chunk_index"]
            }
            for c in retrieved_chunks
        ],
        "usage": {
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "model": "llama-3.1-8b-instant"
        }
    }
