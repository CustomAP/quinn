import os

def lambda_handler(event, context):
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
            print("WEBHOOK_VERIFIED")
            return {
                "statusCode": 200,
                "body": challenge
            }
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            return {
                "statusCode": 403
            }
