import requests
from ciftag.config_templates.get_env import EnvKeys


class Slack:
    def __init__(self) -> None:
        self.url = EnvKeys.SLACK_URI
        self.url_notice = EnvKeys.SLACK_URI_NOTICE

    def send(self, text, channel=None):
        if channel == 'notice':
            requests.post(self.url_notice, json={"text": text})
        else:
            requests.post(self.url, json={"text": text})


