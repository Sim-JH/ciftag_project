from ciftag.services.pinterest import PAGETYPE


def execute_with_logging(action, logs, *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except Exception as e:
        logs.log_data(f"---{PAGETYPE} {action.__name__} Error : {e}")
        return {"result": False, "message": "Run Fail"}
