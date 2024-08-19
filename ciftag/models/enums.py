from enum import Enum


class RunOnCode(Enum):
    local = "0"
    aws = "1"


class StatusCode(Enum):
    active = "0"
    pause = "1"
    inactive = "2"


class HistoryCode(Enum):
    create = "0"
    update = "1"
    delete = "2"
    login = "3"


class UserRole(Enum):
    admin = "0"
    user = "1"


class CrawlTargetCode(Enum):
    pinterest = "1"
    danbooru = "2"


class CrawlStatusCode(Enum):
    load = "0"
    success = "1"
    failed = "2"
    download = "3"
    end = "4"
