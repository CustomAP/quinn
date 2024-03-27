import re
import requests
import time

def send_success_response(response, phone_number_id, token, from_number):
    messages = re.findall('[^.?!\n]+.?', response)

    for message in messages:
        requests.post(
            f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "text": {"body": str(message).strip()}
            },
            headers={"Content-Type": "application/json"}
        )
        time.sleep(2)
    
def send_error_response(phone_number_id, token, from_number):
    requests.post(
        f"https://graph.facebook.com/v18.0/{phone_number_id}/messages?access_token={token}",
        json={
            "messaging_product": "whatsapp",
            "to": from_number,
            "text": {"body": "Sorry something went wrong!"}
        },
        headers={"Content-Type": "application/json"}
    )