import yaml
from helper_functions.messages.format import format_messages_for_summary
from helper_functions.pinecone.index_actions import query_index
from helper_functions.llm_wrapper.open_ai.embeddings.embeddings import openai_embeddings
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call

def get_messages_with_context(user_phone_number, messages):
    summarize_prompt = ""
    with open('prompts/summarize_messages.yaml', 'r') as file:
        summarize_prompt = yaml.safe_load(file)
        summarize_prompt = summarize_prompt["system_prompt"]

    context_messages = messages[max(len(messages) - 5, 0): len(messages)]
    formatted_message = format_messages_for_summary(context_messages)

    print("Messages to summarize: " + formatted_message)

    response = stateless_llm_call({
        "system_prompt": summarize_prompt,
        "messages" : [{"role": "user", "content": formatted_message}]
    })

    print("Summarized message: " + response["message"])

    query_embeddings = openai_embeddings(response["message"])

    query_response = query_index(user_phone_number, query_embeddings)

    print("Similar messages: " + str(query_response))

    all_messages = [{"role": "user", "content": f'Previous context if needed: {str(query_response)}'}]
    all_messages.extend(messages)
    
    return all_messages 