import logging
from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def handler(event, context):
    try:
        if "messages" in event and "model" in event:
            response = openAIClient.chat.completions.create(
                model=event["model"],
                messages=event["messages"]
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