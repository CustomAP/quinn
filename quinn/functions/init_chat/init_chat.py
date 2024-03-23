from openai import OpenAI
import os
import time
import json
import boto3
import logging
from botocore.exceptions import ClientError


openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')


def lambda_handler(event, context):
    try:
        if "phone_number" in event:
            phone_number = event["phone_number"]
            new_thread = openAIClient.beta.threads.create()
            
            user = table.get_item(Key={"phone_number": phone_number})
            item = user['Item']
            
            if not "current_thread_id" in item or item["current_thread_id"] == "":
                response = table.update_item(
                    Key={"phone_number": phone_number},
                    UpdateExpression="set current_thread_id=:t",
                    ExpressionAttributeValues={":t": new_thread.id},
                    ReturnValues="UPDATED_NEW",
                )
                
                return {
                    'success': True,
                    'is_new_thread': True,
                    'current_thread_id': response["Attributes"]["current_thread_id"]
                }
            else:
                return {
                    'success': True,
                    'is_new_thread': False,
                    'current_thread_id': item["current_thread_id"]
                }
        else:
            return {
                'success': False,
                'message': "No phone number sent in params"
            }    
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }
