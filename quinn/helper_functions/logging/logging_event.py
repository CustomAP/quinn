import boto3
import datetime
import logging
import os
import traceback

logs_client = boto3.client('logs')
logger = logging.getLogger()

def create_log_group(user_phone_number):
    log_group_name = f'/aws/lambda/{user_phone_number}'
    response = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)

    if not response['logGroups']:
        logs_client.create_log_group(logGroupName=log_group_name)
        logger.setLevel("INFO")
        logger.info("Successfully created log group for user: " + user_phone_number)
    else:
        logger.setLevel("INFO")
        logger.info(f"Log group already exists for user: {user_phone_number}")

def create_log_stream(user_phone_number, function_name):
    log_group_name = f'/aws/lambda/{user_phone_number}'
    log_stream_name = f'{function_name}-log-stream'

    response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name
    )
    
    if not response['logStreams']:
        logs_client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
        logger.setLevel("INFO")
        logger.info("Successfully created log stream for user " + user_phone_number + " and function: " + function_name)
    else:
        logger.setLevel("INFO")
        logger.info("Log stream already exists for user " + user_phone_number + " and function: " + function_name)

def log_event_for_user(user_phone_number, function_name, message):
    if os.getenv('logger_env') == 'cloud':
        log_group_name = f'/aws/lambda/{user_phone_number}'
        log_stream_name = f'{function_name}-log-stream'
        
        log_event = {
            'timestamp': int(datetime.datetime.now().timestamp()) * 1000,
            'message': message
            }
                        
        response = logs_client.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[log_event]
        )
    else:
        logger.setLevel("INFO")
        logger.info(message)

def log_exception_for_user(user_phone_number, function_name, ex):
    message = "Exception in " + function_name + " : " + str(traceback.print_exception(type(ex), ex, ex.__traceback__))
    if os.getenv('logger_env') == 'cloud':
        log_group_name = f'/aws/lambda/{user_phone_number}'
        log_stream_name = f'{function_name}-log-stream'
        
        log_event = {
            'timestamp': int(datetime.datetime.now().timestamp()) * 1000,
            'message': message
            }
                        
        response = logs_client.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[log_event]
        )
    else:
        logger.setLevel("ERROR")
        logger.exception(message)