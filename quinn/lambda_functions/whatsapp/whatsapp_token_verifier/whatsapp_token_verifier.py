import os
import logging

logger = logging.getLogger()

def lambda_handler(event, context):
    try:
        queryParams = event['queryStringParameters']
        verify_token = os.getenv('VERIFY_TOKEN')

        # Parse params from the webhook verification request
        mode = queryParams.get("hub.mode")
        token = queryParams.get("hub.verify_token")
        challenge = queryParams.get("hub.challenge")

        # Check if a token and mode were sent
        if mode and token:
            # Check the mode and token sent are correct
            if mode == "subscribe" and token == verify_token:
                logger.setLevel("INFO")
                logger.info("Webhook token verified.")
                return {
                    "statusCode": 200,
                    "body": challenge
                }
            else:
                logger.setLevel("INFO")
                logger.info("Webhook token verification failed.")
                return {
                    "statusCode": 403
                }
    except Exception as e:
        logger.setLevel("ERROR")
        logger.exception("Error while performing webhook token verification: " + e)
        return {
            'statusCode': 500
        }
