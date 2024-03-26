import json
import boto3
import logging
import requests
import re
import time
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
import yaml

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
    
def send_success_response(response, phone_number_id, token, from_number):
    messages = re.findall('[^.?!\n]+.?', response)

    for message in messages:
        requests.post(
            f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "text": {"body": str(message).strip()}
            },
            headers={"Content-Type": "application/json"}
        )
        time.sleep(2)
    
def send_error_response(phone_number_id, token, from_number):
    requests.post(
        f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
        json={
            "messaging_product": "whatsapp",
            "to": from_number,
            "text": {"body": "Sorry something went wrong!"}
        },
        headers={"Content-Type": "application/json"}
    )

def get_messages(user_phone_number, user_message):
    user = table.get_item(Key={"phone_number": user_phone_number})
    item = user['Item']

    total_messages = len(item["messages"]) if "message" in item else 0

    with open('prompts/quinn.yaml', 'r') as file:
        quinn_prompt = yaml.safe_load(file)
        messages = [{"role": "system", "content": quinn_prompt["system_prompt"]}]
        if total_messages > 0:
            messages = item["messages"][max(total_messages - 49, 0): total_messages - 1]
        
        messages.append({"role": "user", "content": user_message})
        return messages

def lambda_handler(event, context):
    try:
        if ("user_message" in event and
            "user_phone_number" in event and
            "phone_number_id" in event and
            "token" in event and
            "from_number" in event
            ):
            user_message = event["user_message"]
            user_phone_number = event["user_phone_number"]
            phone_number_id = event["phone_number_id"]
            token = event["token"]
            from_number = event["from_number"]

            messages = get_messages(user_phone_number, user_message)

            response = stateless_llm_call({"messages" : messages})

            if response["success"]:
                replies = [
                    {"role" : "user", "content" : user_message},
                    {"role": "assistant", "content" : response["message"]}
                ]
                
                table.update_item(
                    Key={"phone_number": user_phone_number},
                    UpdateExpression="set messages=list_append(if_not_exists(messages, :emptylist), :m)",
                    ExpressionAttributeValues={
                        ":m" : replies,
                        ":emptylist": [] 
                        }
                )

                send_success_response(response["message"], phone_number_id, token, from_number)
            else:
                print("LLM Response failed" + response["message"])
                send_error_response(phone_number_id, token, from_number)
            
            # TODO add some other logic after X messages summarize and update system prompt
            # if int(open_ai_response_payload["usage"]) > 2000:
            #     print("Summarizing chat")
            #     summarize_chat(user_phone_number)

            
        else:
            print("missing params")
            send_error_response(phone_number_id, token, from_number)
    except Exception as e:
        logging.exception("Error occurred")
        send_error_response(phone_number_id, token, from_number)