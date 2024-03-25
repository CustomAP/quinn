import json
import logging
from openai import OpenAI
import os
import boto3

lambdaClient = boto3.client("lambda")

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

filteror_system_message ='''
You are an assistant that modifies a message as:
If there are too many questions, make them one question.
Make the reply shorter but do not destroy the information. Make sure all the information is still in the reply.
Remove phrases like "Feel free to", "I am here for you", "just let me know", "I'm here to listen and talk with you", "If there's anything you need" etc.
'''

def handler(event, context):
    try:
        if "message" in event:
            open_ai_request = {
                "system_message": filteror_system_message,
                "message": event["message"]
            }
            
            open_ai_response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-open_ai_chat_completion",
                Payload=json.dumps(open_ai_request)
            )
                
            open_ai_response_payload = json.load(open_ai_response["Payload"])

            return {
                "success": open_ai_response_payload["success"],
                "message": open_ai_response_payload["message"],
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