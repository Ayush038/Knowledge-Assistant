def chunk_text(text, chunk_size=300, overlap=60):
    if not text:
        return []

    words = text.split()
    chunks = []

    start = 0
    total_words = len(words)

    while start < total_words:
        end = start + chunk_size
        chunk_words = words[start:end]

        chunks.append(" ".join(chunk_words))

        start = end - overlap

        if start < 0:
            start = 0

    return chunks