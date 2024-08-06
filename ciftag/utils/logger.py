import os
import time
import logging

import pendulum

from ciftag.utils.slack import Slack
from ciftag.configuration import conf
from ciftag.settings import tz_converter


class Logger:
    def __init__(self, log_name: str = None):
        log_folder = conf.get("dir", "base_log_dir")
        today_file = time.strftime("%Y%m%d", tz_converter()) + ".log"

        self.log_path = f"{log_folder}/common"    
        os.makedirs(self.log_path, exist_ok=True)

        if log_name is None:
            self.log_path = f"{self.log_path}/{today_file}"
        else:
            self.log_path = f"{self.log_path}/{log_name}"

        self.logger = logging.getLogger(self.log_path)

        # Handler 세팅
        if not len(self.logger.handlers):
            logging.Formatter.converter = tz_converter  # log 시간대 설정
            log_format = "%(asctime)s %(levelname)-8s %(message)s"
            formatter = logging.Formatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S')

            file_handler = logging.FileHandler(self.log_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # 중복 로그 방지

    def log_data(self, txt: str, level: str = 'info'):
        if level == "debug":
            self.logger.debug(txt)
        elif level == "info":
            self.logger.info(txt)
        elif level == "warning":
            self.logger.warning(txt)
        elif level == "error":
            self.logger.error(txt)
        elif level == "critical":
            self.logger.critical(txt)

        # error 이상 자동 알람
        if level != "debug" and level != "info" and level != "warning":
            try:
                Slack().send(f'Ciftag error {level} : {txt}')
            except Exception as e:
                self.logger.debug(f'Slack Send Error: {e}')

    def get_url(self):
        return self.log_path
