import logging
from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def handler(event, context):
    try:
        if "message" in event:
            messages = []
            if "system_message" in event:
                messages.append({"role": "system", "content": event["system_message"]})
            messages.append({"role": "user", "content": event['message']})

            response = openAIClient.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
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