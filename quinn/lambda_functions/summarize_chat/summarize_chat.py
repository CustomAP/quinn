import os
import boto3
from botocore.exceptions import ClientError
import json
import logging
import yaml
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call


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

def format_messages(messages):
    formatted_messages = ""
    print(messages)
    for message in messages:
        message['content'].replace("\n", " ")
        formatted_messages += f"{message['role']} : {message['content']}\n"
    return formatted_messages

def lambda_handler(event, context):
    try:
        if "phone_number" in event and "messages" in event:
            phone_number = event["phone_number"]
            messages = event["messages"]

            with open("lambda_functions/summarize_chat/summarize.yaml", 'r') as file:
                summarize_file = yaml.safe_load(file)

                formatted_messages = format_messages(json.loads(messages))

                response = stateless_llm_call({
                    "system_prompt": summarize_file["system_prompt"],
                    "messages" : [{"role" : "user", "content": json.dumps(formatted_messages)}]
                    })

                response_json = json.loads(response["message"])
                    
                table.update_item(
                    Key={"phone_number": phone_number},
                    UpdateExpression="set loves=list_append(if_not_exists(loves, :emptylist), :loves), likes=list_append(if_not_exists(likes, :emptylist), :likes), hates=list_append(if_not_exists(hates, :emptylist), :hates), dislikes=list_append(if_not_exists(dilikes, :emptylist), :dislikes),did_today=list_append(if_not_exists(did_today, :emptylist), :did), going_to_do_today=list_append(if_not_exists(going_to_do_today, :emptylist), :today), going_to_do_later=list_append(if_not_exists(going_to_do_later, :emptylist), :later), habits=list_append(if_not_exists(habits, :emptylist), :habits), tone=list_append(if_not_exists(tone, :emptylist), :tone)",
                    ExpressionAttributeValues={
                        ":loves": response_json["Things the user loves"],
                        ":likes": response_json["Things the user likes"],
                        ":hates": response_json["Things the user hates"],
                        ":dislikes": response_json["Things the user dislikes"],
                        ":did": response_json["Things the user did today"],
                        ":today": response_json["Things the user is going to do today"],
                        ":later": response_json["Things the user is going to do tommorrow or later"],
                        ":habits": response_json["Habits of the user"],
                        ":tone": response_json["Tone of the user"],
                        ":emptylist": []
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
                'message': "Missing params"
            }
    except Exception as e:
        logging.exception("Exception occurred")
        return {
            'success': False,
            'message': str(e)
        }