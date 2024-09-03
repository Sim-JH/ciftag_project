import requests
import urllib3

from urllib3 import Retry
from urllib3.exceptions import InsecureRequestWarning

session = None


def get_session(api_proxies: dict):
    global session
    if session is None:
        session = requests_retry_session(api_proxies=api_proxies)
    return session


def requests_retry_session(
    api_proxies: dict,
    retries=3,
    backoff_factor=0.3,
    status_force_list=(500, 502, 503, 504),
    raise_on_status=True,
    _session=None
):
    """ 재시도 하면서 requests용 session 생성 (프록시 존재 시 사용) """
    _session = requests.Session()
    _session.proxies = api_proxies
    _session.hooks = {"response": response_hook}

    Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        raise_on_status=raise_on_status,
        status_forcelist=status_force_list,
    )
    urllib3.disable_warnings(InsecureRequestWarning)

    return _session


def response_hook(response, *args, **kwargs):
    """ 에러 시 출력 처리 """
    if 400 <= response.status_code < 500:
        print(f"Client error occurred: {response.status_code}")


def make_requests(url, api_proxies: dict, method="GET", params=None, data=None, headers=None):
    """ 생성된 세션 없을 시, 새로운 세션 포함 """
    _session = get_session(api_proxies)
    response = _session.request(method, url, params=params, data=data, headers=headers, verify=False, timeout=10)
    return response
