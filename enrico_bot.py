import json
import slack
import os

with open(os.path.join(os.path.dirname(__file__),'API_config_private/fermi1bot_config.json')) as json_file:
    data = json.load(json_file)
    token = data['token']

client = slack.WebClient(token=token)


def post_message(message):
    try:
        response = client.chat_postMessage(
            channel='#enrico_notifications',
            text=message)
        return response
    except:
        print('enrico_bot error')
        pass


def post_image(image_filepath):
    try:
        response = client.files_upload(
            file=image_filepath,
            channels='#enrico_notifications'
        )
        return response
    except:
        print('enrico_bot error')
        pass