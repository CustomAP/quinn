import json
import boto3
import logging
import yaml
import datetime
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
from helper_functions.logging.logging_event import log_event_for_user, log_exception_for_user, create_log_stream
from helper_functions.whatsapp.whatsapp_response import send_error_response, send_success_response
from lambda_functions.process_message.context_augmenter.context_augmenter import get_messages_with_context


dynamodb = boto3.resource("dynamodb")
usersTable = dynamodb.Table('users')
messages_table = dynamodb.Table('messages')

lambdaClient = boto3.client("lambda")
logger = logging.getLogger()

def summarize_chat(user_phone_number, messages, replies):
    total_messages = messages["total_messages"]
    messages["messages"].extend(replies)
    if total_messages != 0 and total_messages % 20 == 0:
        summarize_request= {
            "phone_number": user_phone_number,
            "messages": messages["messages"]
        }
        
        lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-summarize_chat",
            Payload=json.dumps(summarize_request),
            InvocationType="Event"
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

def lambda_handler(event, context):
    if ("user_message" in event and "user_phone_number" in event and
        "phone_number_id" in event and "token" in event and
        "from_number" in event):
        user_message = event["user_message"]
        user_phone_number = event["user_phone_number"]
        phone_number_id = event["phone_number_id"]
        token = event["token"]
        from_number = event["from_number"]
        
        global function_name
        function_name = context.function_name

        try:
            create_log_stream(user_phone_number, context.function_name)

            messages = get_messages(user_phone_number, user_message)

            messages_with_context = get_messages_with_context(user_phone_number, messages["messages"])

            response = stateless_llm_call({
                "system_prompt": messages["system_prompt"],
                "messages" : messages_with_context
                })

            log_event_for_user(user_phone_number, function_name, "Calling statless LLM for message: " + str(messages["messages"]))

            if response["success"]:
                log_event_for_user(user_phone_number, function_name, "Received LLM response.")
                replies = [
                    {"role" : "user", "content" : user_message, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()},
                    {"role": "assistant", "content" : response["message"], "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
                ]
                log_event_for_user(user_phone_number, function_name, "Updating table with replies: " + str(replies))

                messages_table.update_item(
                    Key={"phone_number": user_phone_number},
                    UpdateExpression="set messages=list_append(if_not_exists(messages, :emptylist), :m)",
                    ExpressionAttributeValues={
                        ":m" : replies,
                        ":emptylist": [] 
                        }
                )

                log_event_for_user(user_phone_number, function_name, "Sending user response: " + str(response["message"]))
                send_success_response(response["message"], phone_number_id, token, from_number)
                summarize_chat(user_phone_number, messages, replies)
            else:
                log_event_for_user(user_phone_number, function_name, "Failed to receive LLM response: " + str(response["message"]))
                send_error_response(phone_number_id, token, from_number)
        except Exception as e:
            log_exception_for_user(user_phone_number, function_name, e)
            send_error_response(phone_number_id, token, from_number)
    else:
        logger.setLevel('INFO')
        logger.info("Message processing failed due to missing parameters.")
        send_error_response(phone_number_id, token, from_number)