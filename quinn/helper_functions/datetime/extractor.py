import yaml
import json
import datetime
from helper_functions.llm_wrapper.stateless.stateless_call import stateless_llm_call
from helper_functions.datetime.format import date_string_to_timestamp


def extract_date_range_from_message(message):
    extractor_prompt = ""
    with open('prompts/date_range_extractor.yaml', 'r') as file:
        extractor_prompt = yaml.safe_load(file)
        extractor_prompt = extractor_prompt["system_prompt"]

    current_datetime = datetime.datetime.now() #TODO add user specific timezone in future

    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

    extractor_prompt += f"\nCurrent time is {formatted_datetime}"

    response = stateless_llm_call({
        "system_prompt": extractor_prompt,
        "messages" : [{"role": "user", "content": message}]
    })

    print("Date extractor response: " + response["message"])

    date_range = json.loads(response["message"])
    print("Date range extracted - " + str(date_range))
    if "start" in date_range and "end" in date_range and "time_format" in date_range and date_range["time_format"] == "MM-dd-YYYY":
        return {
            "start": date_string_to_timestamp(date_range["start"]),
            "end": date_string_to_timestamp(date_range["end"]),
            "time_format": date_range["time_format"]
        }
    return None