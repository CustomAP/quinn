import json
import os
import boto3

lambdaClient = boto3.client("lambda")
sqs = boto3.client('sqs')
aggregate_interval = 2

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')

def trigger_queue_receiver(queue_url, user_phone_number, phone_number_id, token, from_number):
    user = table.get_item(Key={"phone_number": user_phone_number})
    item = user['Item']
    if ("is_queue_polling" in item and not item["is_queue_polling"]) or "is_queue_polling" not in item:
        table.update_item(
            Key={"phone_number": user_phone_number},
            UpdateExpression="set is_queue_polling=:i",
            ExpressionAttributeValues={
                ":i" : True,
                }
        )
        summarize_request= {
            "queue_url": queue_url,
            "user_phone_number": user_phone_number,
            "phone_number_id": phone_number_id,
            "token": token,
            "from_number": from_number
        }
        
        lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-queue_receiver",
            Payload=json.dumps(summarize_request),
            InvocationType="Event"
        )
    
def extract_data(body):
    phone_number_id = body["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    display_phone_number = body["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]
    from_number = body["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    msg_body = body["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    user_phone_number = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    
    return (phone_number_id, display_phone_number, from_number, msg_body, user_phone_number)

def get_or_create_sqs_queue(queue_name):
    # Check if the queue exists
    response = sqs.list_queues(QueueNamePrefix=queue_name)
    if 'QueueUrls' in response:
        # Queue already exists, return its URL
        return response['QueueUrls'][0]
    else:
        # Queue doesn't exist, create a new one
        return create_sqs_queue(queue_name)

def create_sqs_queue(queue_name):
    if not queue_name.endswith('.fifo'):
        queue_name += '.fifo'
    response = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            'FifoQueue': 'true',
            'ContentBasedDeduplication': 'true'
        })
    return response['QueueUrl']

def send_message_to_sqs(queue_url, message, user_phone_number):
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message,
        MessageGroupId=user_phone_number
    )

def lambda_handler(event, context):
    token = os.getenv('WHATSAPP_TOKEN')
    body = json.loads(event["body"])
    if body.get("object"):
        if (body.get("entry") and
                body["entry"][0].get("changes") and
                body["entry"][0]["changes"][0].get("value").get("messages") and
                body["entry"][0]["changes"][0].get("value").get("contacts")[0]["wa_id"]):
            phone_number_id, display_phone_number, from_number, msg_body, user_phone_number = extract_data(body)
            print("original message: " + msg_body + " " + from_number + " " + phone_number_id)
            
            queue_url = get_or_create_sqs_queue(user_phone_number)

            trigger_queue_receiver(queue_url, user_phone_number, phone_number_id, token, from_number)

            send_message_to_sqs(queue_url, msg_body, user_phone_number)
            
            return {
                "statusCode": 200
            }
