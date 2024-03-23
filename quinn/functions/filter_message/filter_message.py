import json
import logging
from openai import OpenAI
import os

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

filteror_system_message ='''
You are an assistant that converts "assistant/AI model" style lines to a human style sentence.
If there are too many questions, make them one question.
Make the reply shorter but do not destroy the information. Make sure all the information is still in the reply.
Avoid phrases like "Feel free to", "I am here for you", "just let me know", etc.
'''

def handler(event, context):
    try:
        if "user_message" in event:
            response = openAIClient.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": filteror_system_message},
                    {"role": "user", "content": event["user_message"]}
                ]
            )

            return {
                "success": True,
                "message": response.choices[0].message.content
            }
    except Exception as e:
        logging.exception(e)
        return {
            'success': False,
            'message': str(e)
        }