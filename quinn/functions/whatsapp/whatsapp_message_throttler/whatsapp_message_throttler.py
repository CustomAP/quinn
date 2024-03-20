import boto3
import time

sqs = boto3.client('sqs')
aggregate_interval = 5
last_reset_time = None

def lambda_handler(event, context):
    queue_url = event.get("user_phone_number")
    messages = receive_messages_from_sqs(queue_url)
    
    if messages:
        reset_timer()
    else:
        # No new messages, check if it's time to aggregate
        if time_since_last_reset() >= aggregate_interval:
            # Aggregate and process messages
            aggregated_message = aggregate_messages_from_sqs()
            if aggregated_message:
                print("Aggregated message:", aggregated_message)
                # Process the aggregated message

def receive_messages_from_sqs():
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0  # Non-blocking receive
    )
    messages = response.get('Messages', [])
    if messages:
        print("New message received from SQS queue")
    return messages

def reset_timer():
    global last_reset_time
    last_reset_time = time.time()

def time_since_last_reset():
    global last_reset_time
    if last_reset_time is None:
        return float('inf')  # Return infinity if the timer has never been reset
    return time.time() - last_reset_time

def aggregate_messages_from_sqs():
    aggregated_message = ""
    while True:
        messages = receive_messages_from_sqs()
        if not messages:
            break  # No more messages, stop aggregating
        for message in messages:
            aggregated_message += message['Body']
            # Delete the message from the queue after processing
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
    return aggregated_message