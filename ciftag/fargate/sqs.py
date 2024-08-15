from typing import Any
import boto3
import json
import queue
import time
import os
from subprocess import check_output
from dataclasses import dataclass

from ciftag.settings import env_key
import ciftag.utils.logger as logger

from botocore.exceptions import BotoCoreError, ClientError

logs = logger.Logger()


@dataclass(frozen=True)
class MessageDto:
    """ receipt_handle -> queue 출력 """
    receipt_handle: str
    data: Any

    def __str__(self) -> str:
        return (f'receipt_handle: {self.receipt_handle}\n'
                f'data: {self.data}')


class SqsManger:
    """ AWS SQS interface """
    def __init__(self, server_type, batch_size=1):
        if server_type == "dev":
            self.queue_url = env_key.SQS_URI

        self.batch_size = batch_size
        self.message_handle = ""
        self.client = boto3.client(
            'sqs',
            aws_access_key_id=env_key.SQS_KEY,
            aws_secret_access_key=env_key.SQS_SECRET,
            region_name='ap-northeast-2'
        )

    @staticmethod
    def __retry(func):
        """ sqs 에러 시 네트워크 재설정 후 재시도 """
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, 6):
                time.sleep(10)
                try:
                    return func(self, *args, **kwargs)
                except (BotoCoreError, ClientError) as e:
                    logs.log_data(f'---- {func.__name__} SQS Error {attempt} : {e}')
                    check_output(['iptables', '-F'])
                    check_output(['ip', 'rule', 'add', 'from', 'all', 'lookup', 'main'])
            else:
                logs.log_data(f'---- {func.__name__} SQS Error Fail Retry over')
                return False
        return wrapper

    @__retry
    def get(self):
        """Fetch messages from SQS queue."""
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=self.batch_size
        )

        if 'Messages' in response:
            for message in response['Messages']:
                try:
                    body = json.loads(message['Body'])
                except json.JSONDecodeError:
                    body = message['Body']

                data = MessageDto(
                    receipt_handle=message['ReceiptHandle'],
                    data=body
                )

                self.message_handle = data.receipt_handle
                return data.data

    @__retry
    def delete(self):
        """Delete the last fetched message from the SQS queue."""
        if self.message_handle:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=self.message_handle
            )
            self.message_handle = None

            return True

    @__retry
    def put(self, data: Any):
        """Send a message to the SQS queue."""
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(data),
        )

        return True

