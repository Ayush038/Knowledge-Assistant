from embeddings.embedder import embed_text
from embeddings.pinecone_client import index
from db import db

chunks_collection = db["document_chunks"]


def build_context(chunk):
    prev_chunk = chunks_collection.find_one({
        "document_id": chunk["document_id"],
        "chunk_index": chunk["chunk_index"] - 1
    })

    next_chunk = chunks_collection.find_one({
        "document_id": chunk["document_id"],
        "chunk_index": chunk["chunk_index"] + 1
    })

    parts = []

    if prev_chunk:
        parts.append(prev_chunk["text"])

    parts.append(chunk["text"])

    if next_chunk:
        parts.append(next_chunk["text"])

    return "\n".join(parts)


def ingest_chunks():
    chunks = chunks_collection.find({"embedded": False})

    vectors = []
    pending_updates = []

    for chunk in chunks:
        context_text = build_context(chunk)

        vector = embed_text(context_text)

        vectors.append({
            "id": str(chunk["_id"]),
            "values": vector,
            "metadata": {
                "document_id": str(chunk["document_id"]),
                "chunk_index": chunk["chunk_index"]
            }
        })

        pending_updates.append(chunk["_id"])

        if len(vectors) >= 50:
            index.upsert(vectors=vectors)

            chunks_collection.update_many(
                {"_id": {"$in": pending_updates}},
                {"$set": {"embedded": True}}
            )

            vectors = []
            pending_updates = []

    if vectors:
        index.upsert(vectors=vectors)

        chunks_collection.update_many(
            {"_id": {"$in": pending_updates}},
            {"$set": {"embedded": True}}
        )
