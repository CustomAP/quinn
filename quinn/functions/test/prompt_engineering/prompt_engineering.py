from openai import OpenAI
import os
import time

openAIClient = OpenAI(
    api_key=os.environ.get("openai_access_key"),
    organization=os.environ.get("openai_organization_id"),
)

def handler(event, context):
    try:
        if "conversation" in event:
            test_assistant = openAIClient.beta.assistants.create(
                name= event["assistant"]["name"],
                instructions=event["assistant"]["instructions"],
                description=event["assistant"]["description"],
                model=event["assistant"]["model"]
            )

            test_thread = openAIClient.beta.threads.create()

            replies = []

            for entry in event["conversation"]:
                openAIClient.beta.threads.messages.create(
                    thread_id = test_thread.id,
                    role = entry["role"],
                    content = entry["content"]
                )
                
                test_run = openAIClient.beta.threads.runs.create(
                    thread_id = test_thread.id,
                    assistant_id = test_assistant.id
                )

                while True:
                    test_run = openAIClient.beta.threads.runs.retrieve(
                        thread_id=test_thread.id,
                        run_id=test_run.id
                    ) 
        
                    if test_run.status != "completed":
                        time.sleep(0.25)
                    else:
                        break
                    
                response = openAIClient.beta.threads.messages.list(thread_id=test_thread.id)
                response_message = response.data[0].content[0].text.value
                replies.append(response_message)
            
            return {
                    "success": True,
                    "body": {
                        "replies": replies
                    }
                }
        else:
            return {
                "success": False,
                "message": "No conversation in payload"
            }

    except Exception as e:
        print(e)
        return {
            'success': False,
            'message': str(e)
        }