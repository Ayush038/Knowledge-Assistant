from datetime import datetime



def document_chunk(document_id, chunk_index, text):
    return{
        "document_id": document_id,
        "chunk_index": chunk_index,
        "text": text,
        "embedded": False,
        "created_at": datetime.utcnow()
    }