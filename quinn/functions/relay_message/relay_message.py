import json
import os
import boto3
import time
from openai import OpenAI

openAIClient = OpenAI(
	api_key=os.environ.get("openai_env"),
	organization='org-nQnTgti1i8GBtV2AImNwhkCW',
)


lambdaClient = boto3.client("lambda")

def summarize_chat(user_phone_number):
	summarize_request= {
		"phone_number": user_phone_number
	}
	
	lambdaClient.invoke(
		FunctionName="arn:aws:lambda:us-east-2:471112961630:function:summarizeChat",
		Payload=json.dumps(summarize_request)
		)

def lambda_handler(event, context):
	try:
		if "user_message" in event and "current_thread_id" in event and "user_phone_number" in event:
			user_message = event["user_message"]
			current_thread_id = event["current_thread_id"]
			user_phone_number = event["user_phone_number"]
			
			openAIClient.beta.threads.messages.create(
				thread_id = current_thread_id,
				role = "user",
				content = user_message
			)
			
			message_run = openAIClient.beta.threads.runs.create(
				thread_id = current_thread_id,
				assistant_id ="asst_p4XAcPbitBCw9sxRZZU7kaGA"
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
					
			response = openAIClient.beta.threads.messages.list(thread_id=current_thread_id)
			model_message = response.data[0].content[0].text.value
			
			print(message_run.usage.total_tokens)
			
			if message_run.usage.total_tokens > 2000:
				summarize_chat(user_phone_number)
			
			return {
				"success": True,
				"message": model_message
			}
		else:
			return {
				'success': False,
				'message': "Some params missing"
			}
	except Exception as e:
		print(e)
		return {
			'success': False,
			'message': str(e)
		}