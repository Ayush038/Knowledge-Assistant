import os
import tempfile
import requests
from bson import ObjectId
from datetime import datetime

import cloudinary.uploader

from documents.model import create_document
from documents.chunk_model import document_chunk
from documents.chunk import chunk_text
from documents.text_extractor import extract_text
from db import db
from logger import get_logger

logger = get_logger(__name__)

documents_collection = db["documents"]
chunks_collection = db["document_chunks"]


def upload_document(file, user_id):
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
        raise RuntimeError("Failed to download file from Cloudinary")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(response.content)
        temp_path = tmp.name

    try:
        extracted_text = extract_text(temp_path, file_type)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            logger.warning("Failed to delete temp file: %s", temp_path)

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

    return {
        "document_id": str(document_id),
        "file_url": cloudinary_url
    }
