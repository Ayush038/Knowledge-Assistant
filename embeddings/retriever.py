from embeddings.embedder import embed_text
from embeddings.pinecone_client import index
from bson import ObjectId
from db import db


chunks_collection = db["document_chunks"]



def retrieve_chunks(query: str, top_k: int = 2, user_id=None, is_admin=False):
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

    chunk_query = {"_id": {"$in": chunk_ids}}

    # 🔴 FIX IS HERE
    if not is_admin and user_id:
        allowed_doc_ids = db["documents"].find(
            {"uploaded_by": ObjectId(user_id)},
            {"_id": 1}
        ).distinct("_id")

        chunk_query["document_id"] = {"$in": allowed_doc_ids}

    chunks = list(
        chunks_collection.find(
            chunk_query,
            {"text": 1, "document_id": 1, "chunk_index": 1}
        )
    )

    if not chunks:
        return []

    chunk_map = {str(c["_id"]): c for c in chunks}

    document_ids = list({c["document_id"] for c in chunks})
    documents = {
        str(d["_id"]): d["original_filename"]
        for d in db["documents"].find(
            {"_id": {"$in": document_ids}},
            {"original_filename": 1}
        )
    }

    ordered_results = []

    for match in matches:
        if match["score"] < 0.2:
            continue
        chunk = chunk_map.get(match["id"])
        if not chunk:
            continue

        ordered_results.append({
            "chunk_id": match["id"],
            "score": match["score"],
            "text": chunk["text"],
            "document_id": str(chunk["document_id"]),
            "document_name": documents.get(
                str(chunk["document_id"]), "Unknown Document"
            ),
            "chunk_index": chunk["chunk_index"]
        })
    
    ordered_results.sort(key=lambda x: x["score"], reverse=True)

    return ordered_results