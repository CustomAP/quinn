import json
import os
import boto3
import time
from openai import OpenAI

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')

lambdaClient = boto3.client("lambda")

def summarize_chat(user_phone_number):
    summarize_request= {
        "phone_number": user_phone_number
    }
    
    lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-summarize_chat",
        Payload=json.dumps(summarize_request),
        InvocationType="Event"
    )

def lambda_handler(event, context):
    try:
        if "user_message" in event and "current_thread_id" in event and "user_phone_number" in event:
            user_message = event["user_message"]
            current_thread_id = event["current_thread_id"]
            user_phone_number = event["user_phone_number"]
            
            openAIClient.beta.threads.messages.create(
                thread_id = current_thread_id,
                role = "user",
                content = user_message
            )
            
            message_run = openAIClient.beta.threads.runs.create(
                thread_id = current_thread_id,
                assistant_id =os.environ.get("quinn_assistant_id")
            )
            
            while True:
                message_run = openAIClient.beta.threads.runs.retrieve(
                    thread_id=current_thread_id,
                    run_id=message_run.id
                ) 
    
                if message_run.status != "completed":
                    time.sleep(0.25)
                else:
                    break
                    
            messages = openAIClient.beta.threads.messages.list(thread_id=current_thread_id)
            response_message = messages.data[0].content[0].text.value
            response_role = messages.data[0].role

            request_message = messages.data[1].content[0].text.value
            request_role = messages.data[1].role

            replies = []
            replies.append({
                "role": request_role,
                "message": request_message
            })

            replies.append({
                "role": response_role,
                "message": response_message
            })

            table.update_item(
                Key={"phone_number": user_phone_number},
                UpdateExpression="set messages=list_append(if_not_exists(messages, :emptylist), :m)",
                ExpressionAttributeValues={
                    ":m" : replies,
                    ":emptylist": [] 
                    }
            )
            
            if message_run.usage.total_tokens > 2000:
                print("Summarizing chat")
                summarize_chat(user_phone_number)
            
            return {
                "success": True,
                "message": response_message
            }
        else:
            return {
                'success': False,
                'message': "Some params missing"
            }
    except Exception as e:
        print(e)
        return {
            'success': False,
            'message': str(e)
        }