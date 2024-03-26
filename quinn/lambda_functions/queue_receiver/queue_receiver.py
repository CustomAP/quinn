import boto3
import datetime
import time
import json

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')
sqs = boto3.client('sqs')

last_poll_time = None
messages = []

lambdaClient = boto3.client("lambda")

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