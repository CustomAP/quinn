from helper_functions.datetime.extractor import extract_date_range_from_message

def handler(event, context):
    message = '''
user :  Do you fear them?
assistant : Not fear, just prefer to keep my distance from snakes.
user :  Haha why so
assistant : Just a personal preference. What about you? Any fears?
user :  I feared death last year
'''
    print(str(extract_date_range_from_message(message)))