import traceback

from enum import Enum
from typing import Dict, Any


def enum_to_dict(enum_obj):
    """Enum 객체를 dict로 변환"""
    return {"name": enum_obj.name, "value": enum_obj.value}


def convert_enum_in_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Dict 안의 Enum 객체를 dict로 변환"""
    converted_data = {}

    for key, value in data.items():
        if isinstance(value, Enum):  # Enum 객체인지 확인
            converted_data[key] = enum_to_dict(value)
        elif isinstance(value, dict):  # 내부에 dict가 있는 경우 재귀적으로 처리
            converted_data[key] = convert_enum_in_data(value)
        else:
            converted_data[key] = value

    return converted_data


def get_traceback_str(exc=None) -> str:
    """Traceback most recent call last -> most recent call first 조정 및 출력 포맷 조정"""
    if exc is None:
        lines = traceback.format_exc().strip().split('\n')
    else:
        # 예외 객체의 타입, 예외 객체, traceback을 정확히 전달
        lines = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip().split('\n')

    # 마지막 줄(오류 메시지 부분)을 최상위로 이동
    error_message = lines[-1] if lines else "Unknown Error"
    traceback_lines = lines[:-1]
    formatted_traceback = [error_message] + traceback_lines

    return '\n'.join(formatted_traceback)
