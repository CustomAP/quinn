import json
import os
import boto3
import logging

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

            open_ai_request = {
                "assistant_id": os.getenv("quinn_assistant_id"),
                "thread_id": current_thread_id,
                "message": message
            }
            
            open_ai_response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-open_ai_assistant_conversation",
                Payload=json.dumps(open_ai_request)
                )
                
            open_ai_response_payload = json.load(open_ai_response["Payload"])

            if open_ai_response_payload["success"]:
                response_message = open_ai_response_payload["message"]
                if len(response_message) > 50:
                    filtered_message = filter_message(response_message)
                else:
                    filtered_message = response_message

                request_message = user_message
                request_role = "user"

                replies = []
                replies.append({
                    "role": request_role,
                    "message": request_message
                })

                replies.append({
                    "role": "assistant",
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
                
                if int(open_ai_response_payload["usage"]) > 2000:
                    print("Summarizing chat")
                    summarize_chat(user_phone_number)

                return {
                    "success": True,
                    "message": filtered_message
                }
            else:
               return {
                    "success": False,
                    "message": open_ai_response_payload["message"]
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