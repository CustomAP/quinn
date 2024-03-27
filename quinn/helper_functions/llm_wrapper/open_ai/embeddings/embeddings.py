from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def openai_embeddings(query):
    response = openAIClient.embeddings.create(input=query, model='text-embedding-3-small')
    return response.data[0].embedding
