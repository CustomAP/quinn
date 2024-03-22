import boto3
import time

sqs = boto3.client('sqs')
aggregate_interval = 2

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
    response = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            'FifoQueue': 'true'
        })
    return response['QueueUrl']

def send_message_to_sqs(queue_url, message):
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message
    )
    print("Message sent to", queue_url, ":", message)

def get_queue_size(queue_url):
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes']['ApproximateNumberOfMessages'])

def aggregate_messages_from_sqs(queue_url):
    aggregated_message = ""
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        AttributeNames=['MessageAttributes'],
        MessageAttributeNames=['All'],
        WaitTimeSeconds=0
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
    queue_url = get_or_create_sqs_queue(event.get("user_phone_number"))

    send_message_to_sqs(queue_url, event.get("msg_body"))

    initial_size = get_queue_size(queue_url)

    # Poll the size of the SQS queue after 2 seconds
    time.sleep(2)
    
    current_size = get_queue_size(queue_url)

    if current_size > initial_size:
        print("Size increased from {} to {}. Terminating instance.".format(initial_size, current_size))
    else:
        aggregated_message = aggregate_messages_from_sqs(queue_url)
        #call following logic using aggregated_message