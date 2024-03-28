import yaml
from helper_functions.messages.format import format_messages_for_summary
from helper_functions.pinecone.index_actions import query_index
from helper_functions.llm_wrapper.open_ai.embeddings.embeddings import openai_embeddings
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
from helper_functions.datetime.extractor import extract_date_range_from_message

def get_system_prompt():
    summarize_prompt = ""
    with open('prompts/summarize_messages.yaml', 'r') as file:
        summarize_prompt = yaml.safe_load(file)
        summarize_prompt = summarize_prompt["system_prompt"]
    return summarize_prompt

def get_message_to_summarize(messages):
    context_messages = messages[max(len(messages) - 5, 0): len(messages)]
    formatted_message = format_messages_for_summary(context_messages)
    return formatted_message

def get_summary(summarize_prompt, formatted_message):
    response = stateless_llm_call({
        "system_prompt": summarize_prompt,
        "messages" : [{"role": "user", "content": formatted_message}]
    })

    return response["message"]

def get_similar_messages(summary, user_phone_number):

    query_embeddings = openai_embeddings(summary)

    query_response = query_index(user_phone_number, query_embeddings)
    return query_response

def get_messages_with_context(user_phone_number, messages):
    summarize_prompt = get_system_prompt()
    formatted_message = get_message_to_summarize(messages)

    print("Messages to summarize: " + formatted_message)

    summary = get_summary(summarize_prompt, formatted_message)

    print("Summary: " + summary)

    date_range = extract_date_range_from_message(formatted_message) #TODO: use this range while quering vector db

    similar_messages = get_similar_messages(summary, user_phone_number)
    
    print("Similar messages: " + str(similar_messages))

    all_messages = [{"role": "user", "content": f'Previous context if needed: {str(similar_messages)}'}]
    all_messages.extend(messages)
    
    return all_messages 