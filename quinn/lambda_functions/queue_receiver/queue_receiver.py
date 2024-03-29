import boto3
import datetime
import time
import json
from helper_functions.logging.logging_event import log_event_for_user, log_exception_for_user, create_log_stream
import logging

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')
sqs = boto3.client('sqs')
logger = logging.getLogger()

function_name = None
last_poll_time = None
function_start_time = None
messages = []

lambdaClient = boto3.client("lambda")

def update_table(user_phone_number):
    table.update_item(
        Key={"phone_number": user_phone_number},
        UpdateExpression="set is_queue_polling=:i",
        ExpressionAttributeValues={
            ":i" : False,
            }
    )

def action(queue_url, user_phone_number, phone_number_id, token, from_number):
    global messages
    global last_poll_time
    global function_start_time
    current_time = datetime.datetime.now()
    time_since_last_message = current_time - last_poll_time
    time_since_function_start = current_time - function_start_time
    if time_since_last_message.total_seconds() >= 2:
        if len(messages) and time_since_function_start.total_seconds() < 540:
            process_messages(user_phone_number, phone_number_id, token, from_number)
        elif len(messages) and time_since_function_start.total_seconds() > 540:
            process_messages(user_phone_number, phone_number_id, token, from_number)
            update_table(user_phone_number)
            return True
        elif time_since_last_message.total_seconds() > 120 or time_since_function_start.total_seconds() > 480:
            print("Exiting polling for queue" + queue_url)
            update_table(user_phone_number)
            return True
        messages = []
    else:
        time.sleep(2)
    return False

def mark_message_as_read(phone_number_id, message_id):
    mark_as_read_request = {
        "message_id": message_id,
        "phone_number_id": phone_number_id
    }
    
    lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-whatsapp_mark_as_read",
        Payload=json.dumps(mark_as_read_request),
        InvocationType="Event"
    )

def process_messages(user_phone_number, phone_number_id, token, from_number):
    try:
        aggregated_message = ""
        for message in messages:
            aggregated_message = aggregated_message + " " + message

        relay_request= {
            "user_message": aggregated_message,
            "user_phone_number": user_phone_number,
            "phone_number_id": phone_number_id,
            "token": token,
            "from_number": from_number
        }
        
        log_event_for_user(user_phone_number, function_name, "Starting message processing for message: " + str(aggregated_message))

        lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-process_message",
            Payload=json.dumps(relay_request),
            InvocationType="Event"
        )
        
    except Exception as e:
        log_exception_for_user(user_phone_number, function_name, e)
        return {
            'statusCode' : 500
        }    
    
        
def poll(queue_url, user_phone_number, phone_number_id, token, from_number):
    global messages
    global last_poll_time
    try:
        while True:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            if 'Messages' in response:
                log_event_for_user(user_phone_number, function_name, "Message found in queue: " + str(queue_url))
                last_poll_time = datetime.datetime.now()
                for message in response["Messages"]:
                    json_message = json.loads(message['Body'])
                    messages.append(json_message["message"])
                    mark_message_as_read(phone_number_id, json_message["message_id"])
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
            else:
                try:
                    log_event_for_user(user_phone_number, function_name, "Exiting polling for queue: " + str(queue_url))
                    if action(queue_url, user_phone_number, phone_number_id, token, from_number):
                        break
                except Exception as e:
                    log_exception_for_user(user_phone_number, function_name, e)
                    break
    except Exception as e:
        log_exception_for_user(user_phone_number, function_name, e)
        return {
            'statusCode' : 500
        }

def lambda_handler(event, context):
    queue_url = event["queue_url"]
    user_phone_number = event["user_phone_number"]
    phone_number_id = event["phone_number_id"]
    token = event["token"]
    from_number = event["from_number"]

    global function_name
    function_name = context.function_name

    create_log_stream(user_phone_number, function_name)
    
    try:
        global last_poll_time
        global function_start_time
        last_poll_time = datetime.datetime.now()
        function_start_time = datetime.datetime.now()

        log_event_for_user(user_phone_number, function_name, "Last polling time for queue " + queue_url + " : " + str(last_poll_time))
        poll(queue_url, user_phone_number, phone_number_id, token, from_number)
    except Exception as e:
        log_exception_for_user(user_phone_number, function_name, e)
        return {
            'statusCode': 500
        }