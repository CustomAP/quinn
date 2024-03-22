from openai import OpenAI
import os
import time
import boto3
from botocore.exceptions import ClientError
import json
import logging


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
            
            user = table.get_item(Key={"phone_number": phone_number})
            item = user['Item']

            message_start_index = item["message_start_index"]
            print(item["messages"][int(message_start_index):])

            new_thread = openAIClient.beta.threads.create()
            
            openAIClient.beta.threads.messages.create(
                thread_id = new_thread.id,
                role = "user",
                content = json.dumps(item["messages"][int(message_start_index):])
            )
            
            summary_run = openAIClient.beta.threads.runs.create(
                thread_id = new_thread.id,
                assistant_id =os.environ.get("summarizor_assistant_id")
            )
            
            while True:
                summary_run = openAIClient.beta.threads.runs.retrieve(
                    thread_id=new_thread.id,
                    run_id=summary_run.id
                ) 
    
                if summary_run.status != "completed":
                    time.sleep(0.25)
                else:
                    break
                    
            summary_messages = openAIClient.beta.threads.messages.list(thread_id=new_thread.id)
            summary = summary_messages.data[0].content[0].text.value
            
            if "summaries" in user:
                user["summaries"].append(summary)
            else:
                user["summaries"] = [summary]
                
            table.update_item(
                Key={"phone_number": phone_number},
                UpdateExpression="set summaries=:s",
                ExpressionAttributeValues={":s": user["summaries"]}
                # UpdateExpression="set summaries=:s, current_thread_id=:t",
                # ExpressionAttributeValues={":s": user["summaries"], ":t": ""}
            )
            
            return {
                'success': True
            }
            
        else:
            return {
                'success': False,
                'message': "No phone number sent in params"
            }
    except Exception as e:
        logging.exception("Exception occurred")
        return {
            'success': False,
            'message': str(e)
        }