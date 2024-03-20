import json
import boto3

lambdaClient = boto3.client("lambda")

def lambda_handler(event, context):
    if event.get('queryStringParameters'):
        response = lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-whatsapp_token_verifier",
            Payload=json.dumps(event)
            )
        return json.load(response["Payload"])
    else:
        response = lambdaClient.invoke(
            FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-whatsapp_conversation_handler",
            Payload=json.dumps(event)
            )
        return json.load(response["Payload"])