import json
import os
import boto3
import time
from openai import OpenAI
import logging

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

def get_user_message(user_phone_number, user_message, is_new_thread):
    message = ""
    if is_new_thread:
        user = table.get_item(Key={"phone_number": user_phone_number})
        item = user['Item']
        if "likes" in item or "hates" in item or "did_today" in item or "going_to_do_today" in item or "going_to_do_later" in item or "avoid" in item or "next_convo" in item:
            message = "Metadata from previous conversations:\n"
        if "likes" in item:
            message += f"Things the user likes:\n{json.dumps(item['likes'])}\n"
        if "hates" in item:
            message += f"Things the user hates:\n{json.dumps(item['hates'])}\n"
        # if "did_today" in item:
        #     message += f"Things the user did today:{json.dumps(item['did_today'])}\n"
        # if "going_to_do_today" in item:
        #     message += f"Things the user is going to do today:{json.dumps(item['going_to_do_today'])}\n"
        # if "going_to_do_later" in item:
        #     message += f"Things the user is going to do tomorrow or later:{json.dumps(item['going_to_do_later'])}\n" 
        if "avoid" in item:
            message += f"Things you should avoid talking about with the user:{json.dumps(item['avoid'])}\n"
        # if "next_convo" in item:
        #     message += f"Things you could bring up in your next conversation (cliffhangers):{json.dumps(item['next_convo'])}"
    
        if "messages" in item and len(item["messages"]) > 10:
            message += f"Last 10 messages:\n{json.dumps(item['messages'][len(item['messages']) - 10:])}"

        message += f"Current message:\n{user_message}"
    else:
        message = user_message
    return message

def filter_message(message):
    print("Message before filtering" + message)
    filter_request = {
        "message": message
    }
    
    filter_response = lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-filter_message",
        Payload=json.dumps(filter_request)
    )

    filter_response_payload = json.load(filter_response["Payload"])
    if filter_response_payload["success"]:
        print("Message after filtering" + filter_response_payload["message"])
        return filter_response_payload["message"]
    else:
        raise "Failed to filter message"

def lambda_handler(event, context):
    try:
        if "user_message" in event and "current_thread_id" in event and "user_phone_number" in event and "is_new_thread" in event:
            user_message = event["user_message"]
            current_thread_id = event["current_thread_id"]
            user_phone_number = event["user_phone_number"]
            is_new_thread = event["is_new_thread"]

            message = get_user_message(user_phone_number, user_message, is_new_thread)

            print("original user message: " + user_message)
            
            openAIClient.beta.threads.messages.create(
                thread_id = current_thread_id,
                role = "user",
                content = message
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

            if len(response_message) > 50:
                filtered_message = filter_message(response_message)
            else:
                filtered_message = response_message

            request_message = messages.data[1].content[0].text.value
            request_role = messages.data[1].role

            replies = []
            replies.append({
                "role": request_role,
                "message": request_message
            })

            replies.append({
                "role": response_role,
                "message": filtered_message
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
                "message": filtered_message
            }
        else:
            return {
                'success': False,
                'message': "Some params missing"
            }
    except Exception as e:
        logging.exception("Error occurred")
        return {
            'success': False,
            'message': str(e)
        }