import anthropic
import os
import logging
import json

anthropicClient = anthropic.Anthropic(
    api_key=os.getenv("anthropic_access_key"),
)

def anthropic_message(request):
    if "messages" in request and "model" in request:
        try:
            response = anthropicClient.messages.create(
                model=request["model"],
                max_tokens=1024,
                messages=request["messages"]
            )

            return {
                "success": True,
                "message": response.content[0].text,
                "usage": int(response.usage.input_tokens) + int(response.usage.output_tokens)
            }
        except Exception as e:
            logging.exception("Error occurred")
            return {
                "success": False,
                "message": str(e)
            }
    else:
        return {
            "success": True,
            "message": "Missing params"
        }
