from embeddings.embedder import embed_text
from embeddings.pinecone_client import index
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["KnowledgeAssistant"]
chunks_collection = db["document_chunks"]



def retrieve_chunks(query: str, top_k: int = 2):
    query_vector = embed_text(query)
    search_response = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    matches = search_response.get("matches", [])

    if not matches:
        return []
    
    chunk_ids = [ObjectId(match["id"]) for match in matches]

    chunks = list(
        chunks_collection.find(
            {"_id": {"$in": chunk_ids}},
            {"text": 1, "document_id": 1, "chunk_index": 1}
        )
    )

    chunk_map = {str(chunk["_id"]): chunk for chunk in chunks}

    ordered_results = []

    for match in matches:
        chunk = chunk_map.get(match["id"])
        if chunk:
            ordered_results.append({
                "chunk_id": match["id"],
                "score": match["score"],
                "text": chunk["text"],
                "document_id": str(chunk["document_id"]),
                "chunk_index": chunk["chunk_index"]
            })

    return ordered_results