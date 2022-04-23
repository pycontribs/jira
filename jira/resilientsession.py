import abc
import json
import logging
import random
import time
from typing import Any, Callable, Optional, Union

from requests import Response, Session
from requests.exceptions import ConnectionError
from requests_toolbelt import MultipartEncoder
from typing_extensions import TypeGuard

from jira.exceptions import JIRAError

LOG = logging.getLogger("jira")


def raise_on_error(resp: Optional[Response], **kwargs) -> TypeGuard[Response]:
    """Handle errors from a Jira Request

    Args:
        resp (Optional[Response]): Response from Jira request

    Raises:
        JIRAError: If Response is None
        JIRAError: for unhandled 400 status codes.

    Returns:
        bool: True if the passed in Response is all good.
    """
    request = kwargs.get("request", None)

    if resp is None:
        raise JIRAError(None, **kwargs)

    if not resp.ok:  # equivalent to .status_code < 400 & >200
        error = ""
        if resp.status_code == 403 and "x-authentication-denied-reason" in resp.headers:
            error = resp.headers["x-authentication-denied-reason"]
        elif resp.text:
            try:
                resp_data = json.loads(resp.text)
                if "message" in resp_data:
                    # Jira 5.1 errors
                    error = resp_data["message"]
                elif (
                    "errorMessages" in resp_data and len(resp_data["errorMessages"]) > 0
                ):
                    # Jira 5.0.x error messages sometimes come wrapped in this array
                    # Sometimes this is present but empty
                    errorMessages = resp_data["errorMessages"]
                    if isinstance(errorMessages, (list, tuple)):
                        error = errorMessages[0]
                    else:
                        error = errorMessages
                # Catching only 'errors' that are dict. See https://github.com/pycontribs/jira/issues/350
                elif (
                    "errors" in resp_data
                    and len(resp_data["errors"]) > 0
                    and isinstance(resp_data["errors"], dict)
                ):
                    # Jira 6.x error messages are found in this array.
                    error_list = resp_data["errors"].values()
                    error = ", ".join(error_list)
                else:
                    error = resp.text
            except ValueError:
                error = resp.text

        raise JIRAError(
            error,
            status_code=resp.status_code,
            url=resp.url,
            request=request,
            response=resp,
            **kwargs,
        )

    return True  # if no exception was raised, we have a valid Response


class ResilientSession(Session):
    """This class is supposed to retry requests that do return temporary errors.

    :py:meth:`__recoverable` handles all retry-able errors.
    """

    def __init__(self, timeout=None):
        self.max_retries = 3
        self.max_retry_delay = 60
        self.timeout = timeout
        super().__init__()

        # Indicate our preference for JSON to avoid https://bitbucket.org/bspeakmon/jira-python/issue/46 and https://jira.atlassian.com/browse/JRA-38551
        self.headers.update({"Accept": "application/json,*.*;q=0.9"})

    def _jira_prepare(self, **_kwargs) -> dict:
        """Do any pre-processing of our own and return the updated kwargs (deepcopy)."""
        kwargs = copy.deepcopy(_kwargs)

        data = _kwargs.get("data", {})
        if isinstance(data, dict):
            # mypy ensures we don't do this,
            # but for people subclassing we should preserve old behaviour
            kwargs["data"] = json.dumps(data)
        elif callable(data):
            self._handle_stream(data)

        return kwargs

    def _handle_stream(self, data_callable: Callable) -> Any:
        """Workaround retrying a stream by passing in a callable that produces the data.

        Args:
            data_callable (Callable): The callable that produces the requests' data.

        Returns:
            Any: The requests' data.
        """
        if isinstance(data_callable, MultipartEncoder):
            return data_callable()

    def request(self, method: str, url: Union[str, bytes], **_kwargs) -> Response:  # type: ignore[override]
        """This is an intentional override of `Session.request()` to inject some error handling and retry logic.

        Raises:
            Exception: Various exceptions as defined in py:method:`raise_on_error`.

        Returns:
            Response: The response.
        """

        retry_number = 0
        exception: Optional[Exception] = None
        response: Optional[Response] = None
        response_or_exception: Optional[Union[ConnectionError, Response]]

        processed_kwargs = self._jira_prepare(**_kwargs)

        def is_retrying() -> bool:
            """Helper method to say if we should still be retrying."""
            return retry_number <= self.max_retries

        while is_retrying():
            response = None
            exception = None

            try:
                response = super().request(method, url, **processed_kwargs)
                if response.ok:
                    return response
            # Can catch further exceptions as required below
            except ConnectionError as e:
                exception = e

            # Decide if we should keep retrying
            response_or_exception = response if response is not None else exception
            retry_number += 1
            if is_retrying() and self.__recoverable(
                response_or_exception, url, method.upper(), retry_number
            ):
                if isinstance(_kwargs.get("data"), MultipartEncoder):
                    kwargs = self._jira_prepare(**_kwargs)
            else:
                retry_number = self.max_retries + 1  # exit the while loop, as above max

        if exception is not None:
            # We got an exception we could not recover from
            raise exception
        elif raise_on_error(response, **processed_kwargs):
            # raise_on_error will raise an exception if the response is invalid
            return response
        else:
            # Shouldn't reach here...(but added for mypy's benefit)
            raise RuntimeError("Expected a Response or Exception to raise!")

    def __recoverable(
        self,
        response: Optional[Union[ConnectionError, Response]],
        url: Union[str, bytes],
        request_method: str,
        counter: int = 1,
    ):
        """Return whether the request is recoverable and hence should be retried.

        At this moment it supports: 429

        Args:
            response (Optional[Union[ConnectionError, Response]]): The response or exception.
              Note: the response here is expected to be ``not response.ok``.
            url (Union[str, bytes]): The URL.
            request_method (str): The request method.
            counter (int, optional): The retry counter. Defaults to 1.

        Returns:
            bool: True if the request should be retried.
        """
        is_recoverable = True  # Controls return value AND whether we delay or not
        msg = str(response)

        if isinstance(response, ConnectionError):
            LOG.warning(
                f"Got ConnectionError [{response}] errno:{response.errno} on {request_method} "
                + f"{url}\n{vars(response)}\n{response.__dict__}"  # type: ignore[str-bytes-safe]
            )

        if isinstance(response, Response):
            if response.status_code in [429]:
                is_recoverable = False
                number_of_tokens_issued_per_interval = response.headers[
                    "X-RateLimit-FillRate"
                ]
                token_issuing_rate_interval_seconds = response.headers[
                    "X-RateLimit-Interval-Seconds"
                ]
                maximum_number_of_tokens = response.headers["X-RateLimit-Limit"]
                retry_after = response.headers["retry-after"]
                msg = f"{response.status_code} {response.reason}"
                logging.warning(
                    f"Request rate limited by Jira: request should be retried after {retry_after} seconds.\n"
                    + f"{number_of_tokens_issued_per_interval} tokens are issued every {token_issuing_rate_interval_seconds} seconds. "
                    + f"You can accumulate up to {maximum_number_of_tokens} tokens.\n"
                    + "Consider adding an exemption for the user as explained in: "
                    + "https://confluence.atlassian.com/adminjiraserver/improving-instance-stability-with-rate-limiting-983794911.html"
                )
            elif not (
                response.status_code == 200
                and len(response.content) == 0
                and "X-Seraph-LoginReason" in response.headers
                and "AUTHENTICATED_FAILED" in response.headers["X-Seraph-LoginReason"]
            ):
                is_recoverable = False
            else:
                msg = "Atlassian's bug https://jira.atlassian.com/browse/JRA-41559"

        if is_recoverable:
            # Exponential backoff with full jitter.
            delay = min(self.max_retry_delay, 10 * 2**counter) * random.random()
            LOG.warning(
                "Got recoverable error from %s %s, will retry [%s/%s] in %ss. Err: %s"
                % (request_method, url, counter, self.max_retries, delay, msg)  # type: ignore[str-bytes-safe]
            )
            if isinstance(response, Response):
                LOG.debug("response.headers: %s", response.headers)
                LOG.debug("response.body: %s", response.content)
            time.sleep(delay)

        return is_recoverable
