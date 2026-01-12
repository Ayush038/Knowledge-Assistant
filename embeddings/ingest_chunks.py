from embeddings.embedder import embed_text
from embeddings.pinecone_client import index
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["KnowledgeAssistant"]
chunks_collection = db["document_chunks"]

def ingest_chunks():
    chunks = chunks_collection.find({"embedded": False})

    vectors = []
    pending_updates= []

    for chunk in chunks:
        vector = embed_text(chunk["text"])

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
            pending_updates= []

    if vectors:
        index.upsert(vectors=vectors)
        chunks_collection.update_many(
            {"_id": {"$in": pending_updates}},
            {"$set": {"embedded": True}}
        )
