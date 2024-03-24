import boto3
import datetime
import time
import json
import requests
import re

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')
sqs = boto3.client('sqs')

last_poll_time = None
messages = []

lambdaClient = boto3.client("lambda")

def init_chat(user_phone_number):
    init_request= {
        "phone_number": user_phone_number
    }
    
    init_response = lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-init_chat",
        Payload=json.dumps(init_request)
        )
        
    init_response_payload = json.load(init_response["Payload"])
    return init_response_payload

def relay_message(msg_body, current_thread_id, phone_number_id, token, from_number, user_phone_number, is_new_thread):
    relay_request= {
        "user_message": msg_body,
        "current_thread_id": current_thread_id,
        "user_phone_number": user_phone_number,
        "is_new_thread": is_new_thread
    }
    
    relay_response = lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-relay_message",
        Payload=json.dumps(relay_request)
        )
    
    relay_response_payload = json.load(relay_response["Payload"])
    
    if relay_response_payload["success"]:
        messages = re.findall('[^.?!\n]+.?', relay_response_payload["message"])

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
    else:
       send_error_response(phone_number_id, token, from_number)

def send_error_response(phone_number_id, token, from_number):
    response = requests.post(
        f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
        json={
            "messaging_product": "whatsapp",
            "to": from_number,
            "text": {"body": "Sorry something went wrong!"}
        },
        headers={"Content-Type": "application/json"}
    )

def process_messages(user_phone_number, phone_number_id, token, from_number):
    aggregated_message = ""
    for message in messages:
        aggregated_message = aggregated_message + " " + message['Body']
    init_response_payload = init_chat(user_phone_number)
    if init_response_payload["success"]:
        relay_message(aggregated_message, init_response_payload["current_thread_id"], phone_number_id, token, from_number, user_phone_number, init_response_payload["is_new_thread"])
    else:
        send_error_response(phone_number_id, token, from_number)

def poll(queue_url, user_phone_number, phone_number_id, token, from_number):
    global messages
    global last_poll_time
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5
        )
        if 'Messages' in response:
            print("message found")
            last_poll_time = datetime.datetime.now()
            for message in response["Messages"]:
                messages.append(message)
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message['ReceiptHandle']
                )
        else:
            print("messages now:" + str(messages))
            current_time = datetime.datetime.now()
            duration = current_time - last_poll_time
            if duration.total_seconds() > 120:
                print("Exiting polling for queue" + queue_url)
                table.update_item(
                    Key={"phone_number": user_phone_number},
                    UpdateExpression="set is_queue_polling=:i",
                    ExpressionAttributeValues={
                        ":i" : False,
                        }
                )
                break
            if duration.total_seconds() >= 2:
                if len(messages):
                    process_messages(user_phone_number, phone_number_id, token, from_number)
                messages = []
            else:
                time.sleep(2)

def lambda_handler(event, context):
    queue_url = event["queue_url"]
    user_phone_number = event["user_phone_number"]
    phone_number_id = event["phone_number_id"]
    token = event["token"]
    from_number = event["from_number"]

    global last_poll_time
    last_poll_time = datetime.datetime.now()

    
    poll(queue_url, user_phone_number, phone_number_id, token, from_number)