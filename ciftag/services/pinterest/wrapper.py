import os
import traceback

from ciftag.services.pinterest import PAGETYPE


def get_traceback_str(traceback_obj=None) -> str:
    """traceback most recent call last -> most recent call first 조정 및 출력 포멧 조정"""
    if traceback_obj is None:
        lines = traceback.format_exc().strip().split('\n')
    else:
        if isinstance(traceback_obj, str):
            lines = traceback_obj.strip().split('\n')
        else:
            lines = ''.join(traceback.format_tb(traceback_obj)).strip().split('\n')

    return '\n'.join(lines)


def execute_with_logging(action, logs, *args, **kwargs):
    try:
        return action(logs, *args, **kwargs)
    except Exception as e:
        traceback_str = get_traceback_str(e.__traceback__)
        logs.log_data(f"--- {PAGETYPE} {action.__name__} Error: {e}\n"
                      f"-- Traceback \n"
                      f"{traceback_str}")
        return {"result": False, "message": "Run Fail"}

