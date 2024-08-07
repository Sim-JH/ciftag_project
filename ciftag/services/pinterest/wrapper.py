import traceback

from ciftag.services.pinterest import PAGETYPE


def execute_with_logging(action, logs, *args, **kwargs):
    try:
        return action(logs, *args, **kwargs)
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        logs.log_data(f"--- {PAGETYPE} {action.__name__} Error: {e} Traceback: {traceback_str}")
        return {"result": False, "message": "Run Fail"}
