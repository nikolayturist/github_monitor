import logging
import logging.handlers
from requests.adapters import HTTPAdapter
import requests
from requests.packages.urllib3.util.retry import Retry


DEFAULT_TIMEOUT = 10


def get_console_handler():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(fmt)
    return console_handler


def get_file_handler():
    file_handler = logging.handlers.RotatingFileHandler("logs/github_monitor.log", mode='a', maxBytes=1024 * 1024 * 5,
                                                        backupCount=5)
    # file_handler = logging.FileHandler("logs/github_monitor.log")
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    # print("file logger created")
    return file_handler


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def configure_http_session(key):

    retry_strategy = Retry(
        total=5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"]
    )
    retry_adapter = HTTPAdapter(max_retries=retry_strategy)
    timeout_adapter = TimeoutHTTPAdapter(timeout=DEFAULT_TIMEOUT)

    http = requests.Session()

    git_headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    if key:
        git_headers["Authorization"] = "token " + key

    http.headers.update(git_headers)
    http.mount("https://", timeout_adapter)
    http.mount("https://", retry_adapter)

    # assert_status_hook = lambda response, *args, **kwargs: response.raise_for_status()
    # def assert_status_hook(response, *args, **kwargs):
    #     return response.raise_for_status()

    # def logging_hook(response, *args, **kwargs):
    #     github_logger.debug("############## Request Response: ###############")
    #     github_logger.debug("--> HEADERS: ")
    #     github_logger.debug(str(response.headers))
    #     github_logger.debug("--> BODY: ")
    #     github_logger.debug(str(response.json()))
    #     github_logger.debug("################################################")

    # http.hooks["response"] = [assert_status_hook]
    # if debug_mode == 1:
    #     http.hooks["response"].append(logging_hook)

    return http
