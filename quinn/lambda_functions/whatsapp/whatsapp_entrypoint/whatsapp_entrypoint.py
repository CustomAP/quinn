import json
import boto3
import logging

lambdaClient = boto3.client("lambda")
logger = logging.getLogger()

def lambda_handler(event, context):
    try:
        if event.get('queryStringParameters'):
            logger.setLevel("INFO")
            logger.info("Performing token verification.")
            response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-whatsapp_token_verifier",
                Payload=json.dumps(event)
                )
            return json.load(response["Payload"])
        else:
            logger.setLevel("INFO")
            logger.info("Initiating conversation handling.")
            response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-whatsapp_conversation_handler",
                Payload=json.dumps(event)
                )
            return json.load(response["Payload"])
    except Exception as e:
            logger.setLevel("ERROR")
            logger.exception("Error while performing verification: " + e)
            return {
                'statusCode': 500
            }