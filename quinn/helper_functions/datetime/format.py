import datetime
def date_string_to_timestamp(date_string):
    date_format = "%m-%d-%Y"
    date_object = datetime.datetime.strptime(date_string, date_format)
    unix_timestamp = date_object.timestamp()

    return unix_timestamp