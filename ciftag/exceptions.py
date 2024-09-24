"""Exceptions used by CIFTAG"""
import traceback
from types import TracebackType


class CiftagException(Exception):
    """
    Base class for all Ciftag's errors
    Each custom exception should be derived from this class
    """
    status_code = 500

    def __init__(self, message, status_code=None, **kwargs):
        super().__init__(message)
        self.status_code = status_code if status_code is not None else self.status_code
        self.kwargs = kwargs

    # 역직렬화 설정
    def __reduce__(self):
        return self.__class__, (self.args[0], self.status_code), self.__dict__


class CiftagWorkException(CiftagException):
    """Raise error on request with custom status"""
    def __init__(self, message, status_code, traceback_str=None, **kwargs):
        super().__init__(message, status_code, **kwargs)
        self.traceback_str = traceback_str  # 추가적인 traceback 메시지 저장

    def __str__(self):
        if self.traceback_str:
            return f"Work Error {super().__str__()}"


class CiftagAPIException(CiftagException):
    """Raise error on request with custom status"""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code
