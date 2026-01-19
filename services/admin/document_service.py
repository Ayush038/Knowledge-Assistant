from bson import ObjectId
from datetime import datetime
from db import db

documents_collection = db["documents"]
users_collection = db["users"]


def fetch_all_documents():
    documents = list(
        documents_collection.find(
            {},
            {
                "_id": 1,
                "original_filename": 1,
                "uploaded_by": 1,
                "uploaded_at": 1,
                "chunk_count": 1,
                "status": 1,
                "is_active": 1
            }
        )
    )

    uploader_ids = [
        ObjectId(doc["uploaded_by"])
        for doc in documents
        if ObjectId.is_valid(doc["uploaded_by"])
    ]

    users = {
        str(user["_id"]): user["username"]
        for user in users_collection.find(
            {"_id": {"$in": uploader_ids}},
            {"username": 1}
        )
    }

    for doc in documents:
        doc["_id"] = str(doc["_id"])
        uploader_id = doc["uploaded_by"]
        doc["uploaded_by"] = users.get(uploader_id, "Unknown User")
        doc["created_at"] = doc.pop("uploaded_at", None)

    return {"documents": documents}


def toggle_document_status(document_id):
    document = documents_collection.find_one({"_id": ObjectId(document_id)})

    if not document:
        return None

    new_status = not document.get("is_active", True)

    documents_collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
    )

    return {"document_id": document_id, "is_active": new_status}
