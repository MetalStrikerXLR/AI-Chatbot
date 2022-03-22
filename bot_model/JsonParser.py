import json


def appendJson(new_data, filename):
    with open(filename, 'r+', encoding="utf8") as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_data with file_data inside emp_details
        file_data["intents"].append(new_data)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)
        file.close()


def editJson(edit_data, filename, row_id):
    with open(filename, 'r+', encoding="utf8") as file:
        file_data = json.load(file)
        file.close()

        file_data["intents"][int(row_id)-1]['tag'] = edit_data['tag']
        file_data["intents"][int(row_id)-1]['patterns'] = edit_data['patterns']
        file_data["intents"][int(row_id) - 1]['response_randomizer'] = edit_data['response_randomizer']
        file_data["intents"][int(row_id)-1]['responses'] = edit_data['responses']
        file_data["intents"][int(row_id) - 1]['extra_responses'] = edit_data['extra_responses']
        file_data["intents"][int(row_id) - 1]['choices'] = edit_data['choices']
        file_data["intents"][int(row_id) - 1]['external_link'] = edit_data['external_link']
        file_data["intents"][int(row_id)-1]['context_set'] = edit_data['context_set']
        file_data["intents"][int(row_id)-1]['context_filter'] = edit_data['context_filter']

    with open(filename, 'w', encoding="utf8") as file:
        # convert back to json.
        json.dump(file_data, file, indent=4)
        file.close()


def deleteJson(index, filename):
    with open(filename, 'r+', encoding="utf8") as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        file.close()

        file_data["intents"].pop(int(index)-1)

    # Opening JSON file for Write
    with open(filename, 'w', encoding="utf8") as file:
        # convert back to json.
        json.dump(file_data, file, indent=4)
        file.close()


def intentParser(tag, pattern, res_randomizer, response, extra_responses, choices, link, context_set, context_filter):
    pattern_split = pattern.split(";")
    response_split = response.split("turnIntoList-Jugar")
    extra_response_split = extra_responses
    choices_split = choices.split(";")
    ext_link = link.split("turnIntoList-Jugar")
    context_set = context_set.split("turnIntoList-Jugar")
    context_filter = context_filter.split("turnIntoList-Jugar")

    entry = {
                "tag": tag,
                "patterns": pattern_split,
                "response_randomizer": res_randomizer,
                "responses": response_split,
                "extra_responses": extra_response_split,
                "choices": choices_split,
                "external_link": ext_link,
                "context_set": context_set,
                "context_filter": context_filter
            }

    return entry


def intentDeparser(data, row_id):

    edit_tag = data["intents"][int(row_id) - 1]['tag']
    edit_pattern = ""
    edit_responses = data["intents"][int(row_id) - 1]['responses']
    edit_extra_responses = []
    edit_choices = ""

    # Pattern Get
    for patterns in data["intents"][int(row_id) - 1]['patterns']:
        edit_pattern += patterns + ";"

    edit_pattern = edit_pattern[:-1]

    # Response Randomizer get
    if 'response_randomizer' in data["intents"][int(row_id) - 1]:
        edit_res_randomizer = data["intents"][int(row_id) - 1]['response_randomizer']
    else:
        edit_res_randomizer = ""

    # Extra Response Get
    if 'extra_responses' in data["intents"][int(row_id) - 1]:
        for extra_responses in data["intents"][int(row_id) - 1]['extra_responses']:
            edit_extra_responses.append(extra_responses)
    else:
        edit_extra_responses = []

    # Choices Get
    if 'choices' in data["intents"][int(row_id) - 1]:
        for choices in data["intents"][int(row_id) - 1]['choices']:
            edit_choices += choices + ";"

        edit_choices = edit_choices[:-1]
    else:
        edit_choices = ""

    # External Link Get
    if 'external_link' in data["intents"][int(row_id) - 1]:
        ext_link = data["intents"][int(row_id) - 1]['external_link'][0]
    else:
        ext_link = ""

    # Context Set Get
    if 'context_set' in data["intents"][int(row_id) - 1]:
        edit_context_set = data["intents"][int(row_id) - 1]['context_set'][0]
    else:
        edit_context_set = ""

    # Context Filter Get
    if 'context_filter' in data["intents"][int(row_id) - 1]:
        edit_context_filter = data["intents"][int(row_id) - 1]['context_filter'][0]
    else:
        edit_context_filter = ""

    return [row_id, edit_tag, edit_pattern, edit_res_randomizer, edit_responses, edit_extra_responses, edit_choices, ext_link, edit_context_set, edit_context_filter]
