import json
from openai import OpenAI
import os
import time

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def handler(event, context):
    if "assistant_id" in event and "message" in event:
        try:
            if "thread_id" in event:
                current_thread_id = event["thread_id"]
            else:
                current_thread_id = openAIClient.beta.threads.create().id

            openAIClient.beta.threads.messages.create(
                thread_id = current_thread_id,
                role = "user",
                content = event["message"]
            )
            
            message_run = openAIClient.beta.threads.runs.create(
                thread_id = current_thread_id,
                assistant_id = event["assistant_id"]
            )
            
            while True:
                message_run = openAIClient.beta.threads.runs.retrieve(
                    thread_id=current_thread_id,
                    run_id=message_run.id
                ) 

                if message_run.status != "completed":
                    time.sleep(0.25)
                else:
                    break
                    
            messages = openAIClient.beta.threads.messages.list(thread_id=current_thread_id)
            response_message = messages.data[0].content[0].text.value

            usage = message_run.usage.total_tokens

            return {
                "success": True,
                "message": response_message,
                "usage": usage
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    else:
        return {
            "success": False,
            "message": "Missing params"
        }
