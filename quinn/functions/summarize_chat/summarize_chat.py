import os
import boto3
from botocore.exceptions import ClientError
import json
import logging

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('users')

lambdaClient = boto3.client("lambda")

def summarize(summary):
    likes = summary.split("Things the user likes:")[1].split("Things the user hates:")[0].strip()
    hates = summary.split("Things the user hates:")[1].split("Things the user did today:")[0].strip()
    did_today = summary.split("Things the user did today:")[1].split("Things the user is going to do today:")[0].strip()
    going_to_do_today = summary.split("Things the user is going to do today:")[1].split("Things the user is going to do tomorrow or later")[0].strip()
    going_to_do_later = summary.split("Things the user is going to do tomorrow or later:")[1].split("Things you should avoid talking about with the user:")[0].strip()
    avoid = summary.split("Things you should avoid talking about with the user:")[1].split("Things you should bring up in your next conversation (cliffhangers):")[0].strip()
    next_convo = summary.split("Things you should bring up in your next conversation (cliffhangers):")[1].strip()
    return (likes, hates, did_today, going_to_do_today, going_to_do_later, avoid, next_convo)

def lambda_handler(event, context):
    try:
        if "phone_number" in event:
            phone_number = event["phone_number"]
            
            #TODO - check if can only get the phone number instead of the object
            user = table.get_item(Key={"phone_number": phone_number})
            item = user['Item']

            message_start_index = item["message_start_index"]
            print(item["messages"][int(message_start_index):])

            open_ai_request = {
                "assistant_id": os.environ.get("summarizor_assistant_id"),
                "message": json.dumps(item["messages"][int(message_start_index):])
            }
            
            open_ai_response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-open_ai_assistant_conversation",
                Payload=json.dumps(open_ai_request)
            )
                
            open_ai_response_payload = json.load(open_ai_response["Payload"])

            if open_ai_response_payload["success"]:
                summary = open_ai_response_payload["message"]

                likes, hates, did_today, going_to_do_today, going_to_do_later, avoid, next_convo = summarize(summary)

                print("summarize: ", summarize(summary))
                    
                table.update_item(
                    Key={"phone_number": phone_number},
                    UpdateExpression="set likes=list_append(if_not_exists(likes, :emptylist), :l), hates=list_append(if_not_exists(hates, :emptylist), :h), did_today=list_append(if_not_exists(did_today, :emptylist), :did), going_to_do_today=list_append(if_not_exists(going_to_do_today, :emptylist), :today), going_to_do_later=list_append(if_not_exists(going_to_do_later, :emptylist), :later), avoid=list_append(if_not_exists(avoid, :emptylist), :a), next_convo=list_append(if_not_exists(next_convo, :emptylist), :n), message_start_index=:msi, current_thread_id=:t",
                    ExpressionAttributeValues={
                        ":l": [likes],
                        ":h": [hates],
                        ":did": [did_today],
                        ":today": [going_to_do_today],
                        ":later": [going_to_do_later],
                        ":a": [avoid],
                        ":n": [next_convo],
                        ":msi": len(item["messages"]) - 1,
                        ":emptylist": [],
                        ":t": ""
                        }
                    # UpdateExpression="set summaries=:s, current_thread_id=:t",
                    # ExpressionAttributeValues={":s": user["summaries"], ":t": ""}
                )
                
                return {
                    'success': True
                }
            else:
                return {
                    'success': False,
                    'message': open_ai_response_payload["message"]
                }
        else:
            return {
                'success': False,
                'message': "No phone number sent in params"
            }
    except Exception as e:
        logging.exception("Exception occurred")
        return {
            'success': False,
            'message': str(e)
        }