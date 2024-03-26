import os
import json
import boto3
from helper_functions.llm_wrapper.open_ai.chat_completion.chat_completion import openai_chat_completion
from helper_functions.llm_wrapper.anthropic.message import anthropic_message

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
            
            return openai_chat_completion(openai_request)
        elif llm == "anthropic":
            anthropic_model = os.getenv("anthropic_model")
            anthropic_request = {
                "model": anthropic_model,
                "messages": request["messages"]
            }
            
            return anthropic_message(anthropic_request)
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