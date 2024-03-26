import os
import json
import boto3

lambdaClient = boto3.client("lambda")

def stateless_llm_call(request):
    llm = os.getenv("llm")

    if "messages" in request:
        if llm == "openai":
            openai_model = os.getenv("openai_model")
            openai_request = {
                "model": openai_model,
                "messages": request["messages"]
            }
            
            openai_response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-open_ai_chat_completion",
                Payload=json.dumps(openai_request)
            )
                
            openai_response_payload = json.load(openai_response["Payload"])
            return openai_response_payload
        elif llm == "anthropic":
            anthropic_model = os.getenv("anthropic_model")
            anthropic_request = {
                "model": anthropic_model,
                "messages": request["messages"]
            }
            
            anthropic_response = lambdaClient.invoke(
                FunctionName="arn:aws:lambda:us-east-2:471112961630:function:quinn-dev-anthropic_message",
                Payload=json.dumps(anthropic_request)
            )
                
            anthropic_response_payload = json.load(anthropic_response["Payload"])
            return anthropic_response_payload
        else:
            return {
                "success": False,
                "message": f"No such llm defined {llm}"
            }
    else:
        return {
            "success": False,
            "message": "Missing params"
        }