from datetime import datetime

def create_document(
    filename,
    original_filename,
    file_type,
    uploaded_by,
    cloudinary_url=None,
    cloudinary_public_id=None
):
    return {
        "filename": filename,
        "original_filename": original_filename,
        "file_type": file_type,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.utcnow(),
        "cloudinary_url": cloudinary_url,
        "cloudinary_public_id": cloudinary_public_id,
        "status": "uploaded",
        "is_active": True,
        "chunk_count": 0
    }
