import boto3
import datetime

logs_client = boto3.client('logs')

def log_event_for_user(log_group_name, log_stream_name, message):
    log_event = {
        'timestamp': int(datetime.datetime.now().timestamp()) * 1000,# Timestamp in milliseconds
        'message': message
        }
                    
    response = logs_client.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[log_event]
    )

    return response