from bson import ObjectId
from db import db

documents_collection = db["documents"]


def get_user_documents(*, user_id, role):
    query = {"is_active": True}

    if role != "admin":
        query["uploaded_by"] = ObjectId(user_id)

    documents = list(documents_collection.find(query, {"_id": 0}))

    return {"documents": documents}
