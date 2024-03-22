from openai import OpenAI
import os
import time
import boto3
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
            
            user = table.get_item(Key={"phone_number": phone_number})
            item = user['Item']

            current_thread_id = item["current_thread_id"]
            
            openAIClient.beta.threads.messages.create(
                thread_id = current_thread_id,
                role = "user",
                content = '''
Now create a summary of this conversation and vector embeddings of all topics that you (his friend) can use to hold conversation or go back to the next time.
The summary should be in the format:
Things user likes:
Things user dislikes:
Things user 
'''
            )
            
            summary_run = openAIClient.beta.threads.runs.create(
                thread_id = current_thread_id,
                assistant_id =os.environ.get("quinn_assistant_id")
            )
            
            while True:
                summary_run = openAIClient.beta.threads.runs.retrieve(
                    thread_id=current_thread_id,
                    run_id=summary_run.id
                ) 
    
                if summary_run.status != "completed":
                    time.sleep(0.25)
                else:
                    break
                    
            summary_messages = openAIClient.beta.threads.messages.list(thread_id=current_thread_id)
            summary = summary_messages.data[0].content[0].text.value
            
            if "summaries" in user:
                user["summaries"].append(summary)
            else:
                user["summaries"] = [summary]
                
            messages = []
                
            for i in range(10, 1, -1):
                role = summary_messages.data[i].role
                message = summary_messages.data[i].content[0].text.value
                
                messages.append({"role": role, "message": message})
                
            
            table.update_item(
                Key={"phone_number": phone_number},
                UpdateExpression="set summaries=:s, messages=:m",
                ExpressionAttributeValues={":s": user["summaries"], ":m" : messages}
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
        print(e)
        return {
            'success': False,
            'message': str(e)
        }