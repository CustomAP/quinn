import boto3
import datetime
import time
import json

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')
sqs = boto3.client('sqs')

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

def mark_message_as_read(user_phone_number, message_id):
    pass

def process_messages(user_phone_number, phone_number_id, token, from_number):
    aggregated_message = ""
    for message in messages:
        aggregated_message = aggregated_message + " " + message['Body']

    relay_request= {
        "user_message": aggregated_message,
        "user_phone_number": user_phone_number,
        "phone_number_id": phone_number_id,
        "token": token,
        "from_number": from_number
    }
    
    lambdaClient.invoke(
        FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-process_message",
        Payload=json.dumps(relay_request),
        InvocationType="Event"
    )

def poll(queue_url, user_phone_number, phone_number_id, token, from_number):
    global messages
    global last_poll_time
    global function_start_time
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
            if action(queue_url, user_phone_number, phone_number_id, token, from_number):
                break

def lambda_handler(event, context):
    queue_url = event["queue_url"]
    user_phone_number = event["user_phone_number"]
    phone_number_id = event["phone_number_id"]
    token = event["token"]
    from_number = event["from_number"]

    global last_poll_time
    global function_start_time
    last_poll_time = datetime.datetime.now()
    function_start_time = datetime.datetime.now()

    
    poll(queue_url, user_phone_number, phone_number_id, token, from_number)