import boto3
from botocore.exceptions import ClientError
import json
import logging
import yaml
import datetime
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
from helper_functions.llm_wrapper.open_ai.embeddings.embeddings import openai_embeddings
from helper_functions.pinecone.index_actions import upsert_index
from helper_functions.messages.format import format_messages_for_summary
from helper_functions.datetime.format import date_string_to_timestamp
from helper_functions.datetime.extractor import extract_date_range_from_message


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')

lambdaClient = boto3.client("lambda")

def lambda_handler(event, context):
    try:
        if "phone_number" in event and "messages" in event:
            phone_number = event["phone_number"]
            messages = event["messages"]

            with open("prompts/summarize_chat.yaml", 'r') as file:
                summarize_file = yaml.safe_load(file)

                formatted_messages = format_messages_for_summary(json.loads(messages))

                response = stateless_llm_call({
                    "system_prompt": summarize_file["system_prompt"],
                    "messages" : [{"role" : "user", "content": json.dumps(formatted_messages)}]
                    })

                response_json = json.loads(response["message"])

                print(response_json)

                vectors = []
                for response in response_json:
                    for key, value in response.items():
                        time_range = extract_date_range_from_message(value)
                        vectors.append({
                            "id": value,
                            "values": openai_embeddings(value), 
                            "metadata" : {
                                "date": time_range["start"]
                                }
                            })

                upsert_index(phone_number, vectors)
                
                return {
                    'success': True
                }
        else:
            return {
                'success': False,
                'message': "Missing params"
            }
    except Exception as e:
        logging.exception("Exception occurred")
        return {
            'success': False,
            'message': str(e)
        }