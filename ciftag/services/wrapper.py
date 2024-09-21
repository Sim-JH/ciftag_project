from ciftag.utils.converter import get_traceback_str


def execute_with_logging(action, logs, *args, **kwargs):
    try:
        return action(logs, *args, **kwargs)
    except Exception as e:
        traceback_str = get_traceback_str(e.__traceback__)
        logs.log_data(f'--- {logs.log_dir} {action.__name__} Error: {e}\n'
                      f'-- Traceback \n'
                      f'{traceback_str}', 'error')
        return {"result": False, "message": 'Run Fail', "traceback": traceback_str}

