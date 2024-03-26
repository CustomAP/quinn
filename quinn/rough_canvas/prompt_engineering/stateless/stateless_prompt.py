import yaml
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call

def handler(event, context):
    with open(event["file_name"], 'r') as file:
        quinn_prompt = yaml.safe_load(file)
        messages = [
            {"role": "system", "content": quinn_prompt["system_prompt"]},
            {"role": "user", "content": quinn_prompt["messages"]}
        ]

    response = stateless_llm_call({"messages" : messages})
    print(response)