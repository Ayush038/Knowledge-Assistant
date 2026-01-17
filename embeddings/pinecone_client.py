from pinecone import Pinecone

import os


pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))