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

def get_similar_messages(summary, user_phone_number, date_range):
    query_embeddings = openai_embeddings(summary)

    query_response_without_metadata = query_index(user_phone_number, query_embeddings)
    query_response_with_metadata = None
    if date_range is not None:
        filter = {
            "$and": [
                    {"date": {"$gte": date_range["start"]}},
                    {"date": {"$lte": date_range["end"]}}
                ]}
        query_response_with_metadata = query_index(user_phone_number, query_embeddings, filter=filter)
    return (query_response_without_metadata, query_response_with_metadata)

def get_messages_with_context(user_phone_number, messages):
    summarize_prompt = get_system_prompt()
    formatted_message = get_message_to_summarize(messages)

    print("Messages to summarize: " + formatted_message)

    summary = get_summary(summarize_prompt, formatted_message)

    print("Summary: " + summary)

    date_range = extract_date_range_from_message(formatted_message)

    print("Date range: " + str(date_range))

    similar_messages_without_metadata, similar_messages_with_metadata = get_similar_messages(summary, user_phone_number, date_range)
    
    print("Similar messages without metadata: " + str(similar_messages_without_metadata))
    print("Similar messages with metadata: " + str(similar_messages_with_metadata))
    
    content = f'Previous context if needed:\n'
    if similar_messages_with_metadata is not None:
        content += f"Context between {date_range['start_unformatted']} and {date_range['end_unformatted']} : {str(similar_messages_with_metadata)}\n"
    content += f"General context from past conversations: {str(similar_messages_without_metadata)}"
    all_messages = [{"role": "user", "content": content}]
    all_messages.extend(messages)
    
    return all_messages 