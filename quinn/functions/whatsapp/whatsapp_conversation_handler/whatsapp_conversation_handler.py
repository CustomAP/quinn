import json
import requests
import os
import boto3
import time

lambdaClient = boto3.client("lambda")
sqs = boto3.client('sqs')

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
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "text": {"body": relay_response_payload["message"]}
            },
            headers={"Content-Type": "application/json"}
        )
    else:
       send_error_response(phone_number_id, token, from_number)
       

def get_or_create_sqs_queue(chat_id):
    queue_name = str(chat_id)
    
    # Check if the queue exists
    response = sqs.list_queues(QueueNamePrefix=queue_name)
    if 'QueueUrls' in response:
        # Queue already exists, return its URL
        return response['QueueUrls'][0]
    else:
        # Queue doesn't exist, create a new one
        return create_sqs_queue(queue_name)

def create_sqs_queue(queue_name):
    response = sqs.create_queue(QueueName=queue_name)
    return response['QueueUrl']

def send_message_to_sqs(queue_url, message):
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message
    )
    print("Message sent to SQS queue:", message)

def receive_messages_from_sqs(queue_url):
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=2  # Long polling for 2 seconds
    )
    messages = response.get('Messages', [])
    if messages:
        print("New message received from SQS queue")
    return messages

def aggregate_messages_from_sqs(queue_url):
    aggregated_message = ""
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,  # Adjust as per your requirement
        AttributeNames=['MessageAttributes'],
        MessageAttributeNames=['All'],
        WaitTimeSeconds=5  # Wait for 5 seconds to aggregate messages
    )
    messages = response.get('Messages', [])
    for message in messages:
        aggregated_message += message['Body']
    # Delete all messages from the queue after processing
    if messages:
        sqs.delete_message_batch(
            QueueUrl=queue_url,
            Entries=[{'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']} for msg in messages]
        )
    return aggregated_message

def lambda_handler(event, context):
    token = os.getenv('WHATSAPP_TOKEN')
    body = json.loads(event["body"])
    if body.get("object"):
        if (body.get("entry") and
                body["entry"][0].get("changes") and
                body["entry"][0]["changes"][0].get("value").get("messages") and
                body["entry"][0]["changes"][0].get("value").get("contacts")[0]["wa_id"]):
            phone_number_id, display_phone_number, from_number, msg_body, user_phone_number = extract_data(body)
            
            # #SQS processing here
            # queue_url = get_or_create_sqs_queue(user_phone_number)
            
            # # Wait for 2 seconds
            # time.sleep(2)
            
            # send_message_to_sqs(queue_url, msg_body)
            
            # # Start polling
            # start_time = time.time()
            # while time.time() - start_time < 5:
            #     messages = receive_messages_from_sqs(queue_url)
            #     if messages:
            #         # New message received, reset timer and continue polling
            #         start_time = time.time()
            #     else:
            #         # No new message received for 5 seconds, aggregate and process
            #         aggregated_message = aggregate_messages_from_sqs(queue_url)
            #         if aggregated_message:
            #             print("Aggregated message:", aggregated_message)
            #             # Process the aggregated message
            #             break  # Exit the loop after processing
            
            init_response_payload = init_chat(user_phone_number)
            
            if init_response_payload["success"]:
                relay_message(msg_body, init_response_payload["current_thread_id"], phone_number_id, token, from_number, user_phone_number, init_response_payload["is_new_thread"])
            else:
                send_error_response(phone_number_id, token, from_number)

            return {
                "statusCode": 200
            }
