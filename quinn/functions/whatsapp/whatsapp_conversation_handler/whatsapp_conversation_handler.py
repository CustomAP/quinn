import json
import requests
import os
import boto3
import time
import re

lambdaClient = boto3.client("lambda")
sqs = boto3.client('sqs')
aggregate_interval = 3

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
    
def extract_data(body):
    phone_number_id = body["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    display_phone_number = body["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]
    from_number = body["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    msg_body = body["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    user_phone_number = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    
    return (phone_number_id, display_phone_number, from_number, msg_body, user_phone_number)
    
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
        messages = re.findall('[^.?\n]+.?', relay_response_payload["message"])

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
            time.sleep(0.25)
    else:
       send_error_response(phone_number_id, token, from_number)

# def get_or_create_sqs_queue(chat_id):
#     queue_name = str(chat_id)
    
#     # Check if the queue exists
#     response = sqs.list_queues(QueueNamePrefix=queue_name)
#     if 'QueueUrls' in response:
#         # Queue already exists, return its URL
#         return response['QueueUrls'][0]
#     else:
#         # Queue doesn't exist, create a new one
#         return create_sqs_queue(queue_name)

# def create_sqs_queue(queue_name):
#     response = sqs.create_queue(
#         QueueName=queue_name)
#     return response['QueueUrl']

# def send_message_to_sqs(queue_url, message):
#     response = sqs.send_message(
#         QueueUrl=queue_url,
#         MessageBody=message
#     )
#     print("Message sent to", queue_url, ":", message)

# def get_queue_size(queue_url):
#     response = sqs.get_queue_attributes(
#         QueueUrl=queue_url,
#         AttributeNames=['ApproximateNumberOfMessages']
#     )
#     return int(response['Attributes']['ApproximateNumberOfMessages'])

# def aggregate_messages_from_sqs(queue_url):
#     aggregated_message = ""
#     response = sqs.receive_message(
#         QueueUrl=queue_url,
#         MaxNumberOfMessages=10,
#         AttributeNames=['MessageAttributes'],
#         MessageAttributeNames=['All'],
#         WaitTimeSeconds=0
#     )
#     messages = response.get('Messages', [])
#     for message in messages:
#         aggregated_message = aggregated_message + " " + message['Body']
#     # Delete all messages from the queue after processing
#     if messages:
#         sqs.delete_message_batch(
#             QueueUrl=queue_url,
#             Entries=[{'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']} for msg in messages]
#         )
#     return aggregated_message

def lambda_handler(event, context):
    token = os.getenv('WHATSAPP_TOKEN')
    body = json.loads(event["body"])
    if body.get("object"):
        if (body.get("entry") and
                body["entry"][0].get("changes") and
                body["entry"][0]["changes"][0].get("value").get("messages") and
                body["entry"][0]["changes"][0].get("value").get("contacts")[0]["wa_id"]):
            phone_number_id, display_phone_number, from_number, msg_body, user_phone_number = extract_data(body)
            
            # queue_url = get_or_create_sqs_queue(user_phone_number)

            # send_message_to_sqs(queue_url, msg_body)

            # initial_size = get_queue_size(queue_url)

            # # Poll the size of the SQS queue after 2 seconds
            # time.sleep(aggregate_interval)
    
            # current_size = get_queue_size(queue_url)

            # if current_size == initial_size:
            #     aggregated_message = aggregate_messages_from_sqs(queue_url)
                
            #     print("Message is: ", aggregated_message)
            
            init_response_payload = init_chat(user_phone_number)
        
            if init_response_payload["success"]:
                relay_message(msg_body, init_response_payload["current_thread_id"], phone_number_id, token, from_number, user_phone_number, init_response_payload["is_new_thread"])
            else:
                send_error_response(phone_number_id, token, from_number)

            return {
                "statusCode": 200
            }
