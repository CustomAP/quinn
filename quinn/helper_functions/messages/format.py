def format_messages_for_summary(messages):
    formatted_messages = ""
    print(messages)
    for message in messages:
        message['content'].replace("\n", " ")
        formatted_messages += f"{message['role']} : {message['content']}\n"
    return formatted_messages