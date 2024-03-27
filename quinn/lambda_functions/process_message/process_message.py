import json
import boto3
import logging
import requests
import re
import time
import yaml
import datetime
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
from helper_functions.logging.logging_event import log_event_for_user, create_log_group, create_log_stream
from helper_functions.messages.format import format_messages_for_summary
from helper_functions.pinecone.index_actions import query_index
from helper_functions.llm_wrapper.open_ai.embeddings.embeddings import openai_embeddings


dynamodb = boto3.resource("dynamodb")
usersTable = dynamodb.Table('users')
messages_table = dynamodb.Table('messages')

lambdaClient = boto3.client("lambda")
logger = logging.getLogger()

def summarize_chat(user_phone_number, messages, replies):
    total_messages = messages["total_messages"]
    messages["messages"].extend(replies)
    if total_messages != 0 and total_messages % 50 == 0:
        summarize_request= {
            "phone_number": user_phone_number,
            "messages": messages["messages"]
        }
        
        lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-summarize_chat",
            Payload=json.dumps(summarize_request),
            InvocationType="Event"
        )
    
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
    message_table_result = messages_table.get_item(Key={"phone_number": user_phone_number})
    item = message_table_result['Item']

    total_messages = len(item["messages"]) if "messages" in item else 0

    quinn_prompt = ""
    with open('prompts/quinn.yaml', 'r') as file:
        quinn_prompt = yaml.safe_load(file)
        quinn_prompt = quinn_prompt["system_prompt"]

    messages = []
    if total_messages > 0:
        for message in item["messages"][max(total_messages - 49, 0): total_messages]:
            messages.append({"role": message["role"], "content": message["content"]})
    
    messages.append({"role": "user", "content": user_message})

    return {"system_prompt" : quinn_prompt, "messages" : messages, "total_messages" : total_messages}

def get_messages_with_context(user_phone_number, messages):
    system_prompt = '''
Role:
You will be given a conversation between Assistant and the user.
You have to create a summarization including all entities in the context.

Output format (very important):
Reply with maximum of 10 words
'''
    context_messages = messages[max(len(messages) - 5, 0): len(messages)]
    print("here")
    formatted_message = format_messages_for_summary(context_messages)

    print(formatted_message)

    response = stateless_llm_call({
        "system_prompt": system_prompt,
        "messages" : [{"role": "user", "content": formatted_message}]
    })

    print(response["message"])

    query_embeddings = openai_embeddings(response["message"])

    print(query_embeddings)

    query_response = query_index(user_phone_number, query_embeddings, top_k=1)

    print(query_response)

    all_messages = [{"role": "user", "content": f'Previous context if needed: {str(query_response)}'}]
    all_messages.extend(messages)

    print(all_messages)
    
    return all_messages    

def lambda_handler(event, context):
    if ("user_message" in event and "user_phone_number" in event and
        "phone_number_id" in event and "token" in event and
        "from_number" in event):
        user_message = event["user_message"]
        user_phone_number = event["user_phone_number"]
        phone_number_id = event["phone_number_id"]
        token = event["token"]
        from_number = event["from_number"]

        function_name = context.function_name
        log_group_name = create_log_group(user_phone_number)
        log_stream_name = create_log_stream(user_phone_number, function_name)

        logger.setLevel('INFO')
        logger.info("Function name and log stream name: " + function_name + " " + log_stream_name)
        
        try:
            messages = get_messages(user_phone_number, user_message)

            messages_with_context = get_messages_with_context(user_phone_number, messages["messages"])

            response = stateless_llm_call({
                "system_prompt": messages["system_prompt"],
                "messages" : messages_with_context
                })

            log_event_for_user(log_group_name, log_stream_name, "Calling statless LLM for message: " + str(messages["messages"]))

            if response["success"]:
                log_event_for_user(log_group_name, log_stream_name, "Received LLM response.")
                replies = [
                    {"role" : "user", "content" : user_message, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()},
                    {"role": "assistant", "content" : response["message"], "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
                ]
                log_event_for_user(log_group_name, log_stream_name, "Updating table with replies: " + str(replies))

                messages_table.update_item(
                    Key={"phone_number": user_phone_number},
                    UpdateExpression="set messages=list_append(if_not_exists(messages, :emptylist), :m)",
                    ExpressionAttributeValues={
                        ":m" : replies,
                        ":emptylist": [] 
                        }
                )

                log_event_for_user(log_group_name, log_stream_name, "Sending user response: " + str(response["message"]))
                send_success_response(response["message"], phone_number_id, token, from_number)
                summarize_chat(user_phone_number, messages, replies)
            else:
                log_event_for_user(log_group_name, log_stream_name, "Failed to receive LLM response: " + str(response["message"]))
                send_error_response(phone_number_id, token, from_number)
        except Exception as e:
            print(str(e))
            log_event_for_user(log_group_name, log_stream_name, "Exception in processing message: " + str(e))
            send_error_response(phone_number_id, token, from_number)
    else:
        logger.setLevel('INFO')
        logger.info("Message processing failed due to missing parameters.")
        send_error_response(phone_number_id, token, from_number)