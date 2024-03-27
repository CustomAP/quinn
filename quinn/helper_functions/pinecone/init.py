from pinecone import Pinecone, ServerlessSpec
import os

def init_pinecone(user_phone_number):
    pinecone = Pinecone(api_key=os.getenv("pinecone_access_key"))
    pinecone.create_index(
        name=str(user_phone_number),
        dimension=512,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        ) 
    )