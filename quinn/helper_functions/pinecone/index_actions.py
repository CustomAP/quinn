from pinecone import Pinecone
import os

pinecone = Pinecone(api_key=os.getenv("pinecone_access_key"))

def upsert_index(index_name, vectors):
    pinecone.Index(index_name).upsert(vectors)

def query_index(index_name, query_embedding, top_k = 5, filter=None, namespace=None):
    index = pinecone.Index(index_name)
    results = []
    if namespace is not None:
        matches = index.query(vector=query_embedding, top_k=top_k, namespace=namespace)['matches']
    elif filter is not None:
        matches = index.query(vector=query_embedding, top_k=top_k, filter=filter)['matches']
    else:
        matches = index.query(vector=query_embedding, top_k=top_k)['matches']

    for match in matches:
        results.append(match["id"])

    return results