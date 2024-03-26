import requests
import os
import time

def lambda_handler(event, context):
    try:
        if "message_id" in event and "phone_number_id" in event:
            time.sleep(2)
            phone_number_id = event['phone_number_id']
            message_id = event["message_id"]
            token = os.getenv("WHATSAPP_TOKEN")
            response = requests.post(
                f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id
                },
                headers={"Content-Type": "application/json"}
            )
            print(response)
    except Exception as e:
        print(str(e))
