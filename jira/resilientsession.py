# -*- coding: utf-8 -*-
import json
import logging
import random
import time
from typing import Callable, Optional, Union, cast

from requests import Response, Session
from requests.exceptions import ConnectionError

from jira.exceptions import JIRAError

logging.getLogger("jira").addHandler(logging.NullHandler())


def raise_on_error(r: Optional[Response], verb="???", **kwargs):
    """Handle errors from a Jira Request

    Args:
        r (Optional[Response]): Response from Jira request
        verb (Optional[str]): Request type, e.g. POST. Defaults to "???".

    Raises:
        JIRAError: If Response is None
        JIRAError: for unhandled 400 status codes.
        JIRAError: for unhandled 200 status codes.
    """
    request = kwargs.get("request", None)
    # headers = kwargs.get('headers', None)

    if r is None:
        raise JIRAError(None, **kwargs)

    if r.status_code >= 400:
        error = ""
        if r.status_code == 403 and "x-authentication-denied-reason" in r.headers:
            error = r.headers["x-authentication-denied-reason"]
        elif r.text:
            try:
                response = json.loads(r.text)
                if "message" in response:
                    # Jira 5.1 errors
                    error = response["message"]
                elif "errorMessages" in response and len(response["errorMessages"]) > 0:
                    # Jira 5.0.x error messages sometimes come wrapped in this array
                    # Sometimes this is present but empty
                    errorMessages = response["errorMessages"]
                    if isinstance(errorMessages, (list, tuple)):
                        error = errorMessages[0]
                    else:
                        error = errorMessages
                # Catching only 'errors' that are dict. See https://github.com/pycontribs/jira/issues/350
                elif (
                    "errors" in response
                    and len(response["errors"]) > 0
                    and isinstance(response["errors"], dict)
                ):
                    # Jira 6.x error messages are found in this array.
                    error_list = response["errors"].values()
                    error = ", ".join(error_list)
                else:
                    error = r.text
            except ValueError:
                error = r.text
        raise JIRAError(
            error,
            status_code=r.status_code,
            url=r.url,
            request=request,
            response=r,
            **kwargs,
        )
    # for debugging weird errors on CI
    if r.status_code not in [200, 201, 202, 204]:
        raise JIRAError(
            status_code=r.status_code, request=request, response=r, **kwargs
        )
    # testing for the bug exposed on
    # https://answers.atlassian.com/questions/11457054/answers/11975162
    if (
        r.status_code == 200
        and len(r.content) == 0
        and "X-Seraph-LoginReason" in r.headers
        and "AUTHENTICATED_FAILED" in r.headers["X-Seraph-LoginReason"]
    ):
        pass


class ResilientSession(Session):
    """This class is supposed to retry requests that do return temporary errors.

    At this moment it supports: 502, 503, 504
    """

    def __init__(self, timeout=None):
        self.max_retries = 3
        self.max_retry_delay = 60
        self.timeout = timeout
        super(ResilientSession, self).__init__()

        # Indicate our preference for JSON to avoid https://bitbucket.org/bspeakmon/jira-python/issue/46 and https://jira.atlassian.com/browse/JRA-38551
        self.headers.update({"Accept": "application/json,*.*;q=0.9"})

    def __recoverable(
        self,
        response: Optional[Union[ConnectionError, Response]],
        url: str,
        request,
        counter: int = 1,
    ):
        msg = str(response)
        if isinstance(response, ConnectionError):
            logging.warning(
                f"Got ConnectionError [{response}] errno:{response.errno} on {request} {url}\n{vars(response)}\n{response.__dict__}"
            )
        if isinstance(response, Response):
            if response.status_code in [502, 503, 504, 401]:
                # 401 UNAUTHORIZED still randomly returned by Atlassian Cloud as of 2017-01-16
                msg = f"{response.status_code} {response.reason}"
                # 2019-07-25: Disabled recovery for codes above^
                return False
            elif not (
                response.status_code == 200
                and len(response.content) == 0
                and "X-Seraph-LoginReason" in response.headers
                and "AUTHENTICATED_FAILED" in response.headers["X-Seraph-LoginReason"]
            ):
                return False
            else:
                msg = "Atlassian's bug https://jira.atlassian.com/browse/JRA-41559"

        # Exponential backoff with full jitter.
        delay = min(self.max_retry_delay, 10 * 2 ** counter) * random.random()
        logging.warning(
            "Got recoverable error from %s %s, will retry [%s/%s] in %ss. Err: %s"
            % (request, url, counter, self.max_retries, delay, msg)
        )
        if isinstance(response, Response):
            logging.debug("response.headers: %s", response.headers)
            logging.debug("response.body: %s", response.content)
        time.sleep(delay)
        return True

    def __verb(
        self, verb: str, url: str, retry_data: Callable = None, **kwargs
    ) -> Response:

        d = self.headers.copy()
        d.update(kwargs.get("headers", {}))
        kwargs["headers"] = d

        # if we pass a dictionary as the 'data' we assume we want to send json
        # data
        data = kwargs.get("data", {})
        if isinstance(data, dict):
            data = json.dumps(data)

        retry_number = 0
        exception = None
        response = None
        while retry_number <= self.max_retries:
            response = None
            exception = None
            try:
                method = getattr(super(ResilientSession, self), verb.lower())
                response = method(url, timeout=self.timeout, **kwargs)
                if response.status_code >= 200 and response.status_code <= 299:
                    return response
            except ConnectionError as e:
                logging.warning(f"{e} while doing {verb.upper()} {url}")

                exception = e
            retry_number += 1

            if retry_number <= self.max_retries:
                response_or_exception = response if response is not None else exception
                if self.__recoverable(
                    response_or_exception, url, verb.upper(), retry_number
                ):
                    if retry_data:
                        # if data is a stream, we cannot just read again from it,
                        # retry_data() will give us a new stream with the data
                        kwargs["data"] = retry_data()
                    continue
                else:
                    break

        if exception is not None:
            raise exception
        raise_on_error(response, verb=verb, **kwargs)
        # after raise_on_error, only Response objects are allowed through
        response = cast(Response, response)  # tell mypy only Response-like are here
        return response

    def get(self, url: Union[str, bytes], **kwargs) -> Response:  # type: ignore
        return self.__verb("GET", str(url), **kwargs)

    def post(self, url: Union[str, bytes], data=None, json=None, **kwargs) -> Response:  # type: ignore
        return self.__verb("POST", str(url), data=data, json=json, **kwargs)

    def put(self, url: Union[str, bytes], data=None, **kwargs) -> Response:  # type: ignore
        return self.__verb("PUT", str(url), data=data, **kwargs)

    def delete(self, url: Union[str, bytes], **kwargs) -> Response:  # type: ignore
        return self.__verb("DELETE", str(url), **kwargs)

    def head(self, url: Union[str, bytes], **kwargs) -> Response:  # type: ignore
        return self.__verb("HEAD", str(url), **kwargs)

    def patch(self, url: Union[str, bytes], data=None, **kwargs) -> Response:  # type: ignore
        return self.__verb("PATCH", str(url), data=data, **kwargs)

    def options(self, url: Union[str, bytes], **kwargs) -> Response:  # type: ignore
        return self.__verb("OPTIONS", str(url), **kwargs)
