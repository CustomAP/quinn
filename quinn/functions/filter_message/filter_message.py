import logging
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call

filteror_system_message ='''
You are an assistant that modifies a message as:
If there are too many questions, make them one question.
Make the reply shorter but do not destroy the information. Make sure all the information is still in the reply.
Remove phrases like "Feel free to", "I am here for you", "just let me know", "I'm here to listen and talk with you", "If there's anything you need" etc.
'''

def handler(event, context):
    try:
        if "message" in event:
            llm_request = {
                "messages": [
                    {"role": "system", "content" : filteror_system_message},
                    {"role": "user", "content" : event["message"]}
                ]
            }
            
            response_payload = stateless_llm_call(llm_request)

            return {
                "success": response_payload["success"],
                "message": response_payload["message"],
            }
        else:
            return {
                "success": False,
                "message": "Missing params"
            }
    except Exception as e:
        logging.exception(e)
        return {
            'success': False,
            'message': str(e)
        }