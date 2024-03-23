import json
import logging
from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

filteror_system_message ='''
You are an assistant that modifies a message as:
If there are too many questions, make them one question.
Remove phrases like "Feel free to", "I am here for you", "just let me know", "I'm here to listen and talk with you", "If there's anything you need" etc.
'''

def handler(event, context):
    try:
        if "message" in event:
            response = openAIClient.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": filteror_system_message},
                    {"role": "user", "content": f"Message to convert:\n{event['message']}"}
                ]
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