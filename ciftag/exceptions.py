"""Exceptions used by CIFTAG"""


class CIFTAGException(Exception):
    """
    Base class for all SIASO's errors
    Each custom exception should be derived from this class
    """
    status_code = 500


class CIFTAGWorkException(CIFTAGException):
    """Raise error on request with custom status_code"""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code

class CIFTAGAPIException(CIFTAGException):
    """Raise error on request with custom status_code"""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code
