import logging
from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def openai_chat_completion(request):
    try:
        if "messages" in request and "model" in request:
            response = openAIClient.chat.completions.create(
                model=request["model"],
                messages=request["messages"]
            )

            return {
                "success": True,
                "message": response.choices[0].message.content
            }
        else:
            return {
                "success": False,
                "message": "Missing params"
            }
    except Exception as e:
        logging.exception(e)
        return {
            'success': False,
            'message': str(e)
        }