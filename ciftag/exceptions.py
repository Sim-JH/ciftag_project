"""Exceptions used by CIFTAG"""


class CIFTAGException(Exception):
    """
    Base class for all SIASO's errors
    Each custom exception should be derived from this class
    """
    status_code = 500


class CIFTAGRequestException(CIFTAGException):
    """Raise error on request with custom status_code"""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


# TODO 따로 관리 필요하려나?
class CIFTAGModuleException(CIFTAGException):
    """Raise error on module with custom status_code"""
    def __init__(self, msg, code):
        super().__init__(f'{msg} --on module')
        self.status_code = code


class CIFTAGFargateException(CIFTAGException):
    """Raise error on fargate with custom status_code"""
    def __init__(self, msg, code):
        super().__init__(f'{msg} --on ecs fargate')
        self.status_code = code