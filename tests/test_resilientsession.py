from __future__ import annotations

import logging
from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from requests import Response

import jira.resilientsession
from jira.exceptions import JIRAError
from jira.resilientsession import parse_error_msg, parse_errors
from tests.conftest import JiraTestCase


class ListLoggingHandler(logging.Handler):
    """A logging handler that records all events in a list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def reset(self):
        self.records = []


class ResilientSessionLoggingConfidentialityTests(JiraTestCase):
    """No sensitive data shall be written to the log."""

    def setUp(self):
        self.loggingHandler = ListLoggingHandler()
        jira.resilientsession.logging.getLogger().addHandler(self.loggingHandler)

    def test_logging_with_connection_error(self):
        """No sensitive data shall be written to the log in case of a connection error."""
        witness = "etwhpxbhfniqnbbjoqvw"  # random string; hopefully unique
        for max_retries in (0, 1):
            for verb in ("get", "post", "put", "delete", "head", "patch", "options"):
                with self.subTest(max_retries=max_retries, verb=verb):
                    with jira.resilientsession.ResilientSession() as session:
                        session.max_retries = max_retries
                        session.max_retry_delay = 0
                        try:
                            getattr(session, verb)(
                                "http://127.0.0.1:9",
                                headers={"sensitive_header": witness},
                                data={"sensitive_data": witness},
                            )
                        except jira.resilientsession.ConnectionError:
                            pass
                    # check that `witness` does not appear in log
                    for record in self.loggingHandler.records:
                        self.assertNotIn(witness, record.msg)
                        for arg in record.args:
                            self.assertNotIn(witness, str(arg))
                        self.assertNotIn(witness, str(record))
                    self.loggingHandler.reset()

    def tearDown(self):
        jira.resilientsession.logging.getLogger().removeHandler(self.loggingHandler)
        del self.loggingHandler


# Retry test data tuples: (status_code, with_rate_limit_header, with_retry_after_header, retry_expected)
with_rate_limit = True
with_retry_after = 1
without_rate_limit = False
without_retry_after = None
status_codes_retries_test_data = [
    # Always retry 429 responses
    (HTTPStatus.TOO_MANY_REQUESTS, with_rate_limit, with_retry_after, True),
    (HTTPStatus.TOO_MANY_REQUESTS, with_rate_limit, 0, True),
    (HTTPStatus.TOO_MANY_REQUESTS, with_rate_limit, without_retry_after, True),
    (HTTPStatus.TOO_MANY_REQUESTS, without_rate_limit, with_retry_after, True),
    (HTTPStatus.TOO_MANY_REQUESTS, without_rate_limit, 0, True),
    (HTTPStatus.TOO_MANY_REQUESTS, without_rate_limit, without_retry_after, True),
    # Retry 503 responses only when 'Retry-After' in headers
    (HTTPStatus.SERVICE_UNAVAILABLE, with_rate_limit, with_retry_after, True),
    (HTTPStatus.SERVICE_UNAVAILABLE, with_rate_limit, without_retry_after, False),
    (HTTPStatus.SERVICE_UNAVAILABLE, without_rate_limit, with_retry_after, True),
    (HTTPStatus.SERVICE_UNAVAILABLE, without_rate_limit, without_retry_after, False),
    # Never retry other responses
    (HTTPStatus.UNAUTHORIZED, with_rate_limit, with_retry_after, False),
    (HTTPStatus.UNAUTHORIZED, without_rate_limit, without_retry_after, False),
    (HTTPStatus.FORBIDDEN, with_rate_limit, with_retry_after, False),
    (HTTPStatus.FORBIDDEN, without_rate_limit, without_retry_after, False),
    (HTTPStatus.NOT_FOUND, with_rate_limit, with_retry_after, False),
    (HTTPStatus.NOT_FOUND, without_rate_limit, without_retry_after, False),
    (HTTPStatus.BAD_GATEWAY, with_rate_limit, with_retry_after, False),
    (HTTPStatus.BAD_GATEWAY, without_rate_limit, without_retry_after, False),
    (HTTPStatus.GATEWAY_TIMEOUT, with_rate_limit, with_retry_after, False),
    (HTTPStatus.GATEWAY_TIMEOUT, without_rate_limit, without_retry_after, False),
]


@patch("requests.Session.request")
@patch(f"{jira.resilientsession.__name__}.time.sleep")
@pytest.mark.parametrize(
    "status_code,with_rate_limit_header,with_retry_after_header,retry_expected",
    status_codes_retries_test_data,
)
def test_status_codes_retries(
    mocked_sleep_method: Mock,
    mocked_request_method: Mock,
    status_code: int,
    with_rate_limit_header: bool,
    with_retry_after_header: int | None,
    retry_expected: bool,
):
    RETRY_AFTER_SECONDS = with_retry_after_header or 0
    RETRY_AFTER_HEADER = {"Retry-After": f"{RETRY_AFTER_SECONDS}"}
    RATE_LIMIT_HEADERS = {
        "X-RateLimit-FillRate": "1",
        "X-RateLimit-Interval-Seconds": "1",
        "X-RateLimit-Limit": "1",
    }

    max_retries = 2

    if retry_expected:
        expected_number_of_requests = 1 + max_retries
        expected_number_of_sleep_invocations = max_retries
    else:
        expected_number_of_requests = 1
        expected_number_of_sleep_invocations = 0

    mocked_response: Response = Response()
    mocked_response.status_code = status_code
    if with_retry_after_header is not None:
        mocked_response.headers.update(RETRY_AFTER_HEADER)
    if with_rate_limit_header:
        mocked_response.headers.update(RATE_LIMIT_HEADERS)

    mocked_request_method.return_value = mocked_response

    session: jira.resilientsession.ResilientSession = (
        jira.resilientsession.ResilientSession(max_retries=max_retries)
    )

    with pytest.raises(JIRAError):
        session.get("mocked_url")

    assert mocked_request_method.call_count == expected_number_of_requests
    assert mocked_sleep_method.call_count == expected_number_of_sleep_invocations

    for actual_sleep in (
        call_args.args[0] for call_args in mocked_sleep_method.call_args_list
    ):
        assert actual_sleep >= RETRY_AFTER_SECONDS


errors_parsing_test_data = [
    (403, {"x-authentication-denied-reason": "err1"}, "", ["err1"]),
    (500, {}, "err1", ["err1"]),
    (500, {}, '{"message": "err1"}', ["err1"]),
    (500, {}, '{"errorMessages": "err1"}', ["err1"]),
    (500, {}, '{"errorMessages": ["err1", "err2"]}', ["err1", "err2"]),
    (500, {}, '{"errors": {"code1": "err1", "code2": "err2"}}', ["err1", "err2"]),
    (
        500,
        {},
        '{"errorMessages": [], "errors": {"code1": "err1", "code2": "err2"}}',
        ["err1", "err2"],
    ),
]


@pytest.mark.parametrize(
    "status_code,headers,content,expected_errors",
    errors_parsing_test_data,
)
def test_error_parsing(status_code, headers, content, expected_errors):
    mocked_response: Response = Response()
    mocked_response.status_code = status_code
    mocked_response.headers.update(headers)
    mocked_response._content = content.encode("utf-8")
    errors = parse_errors(mocked_response)
    assert errors == expected_errors
    error_msg = parse_error_msg(mocked_response)
    assert error_msg == ", ".join(expected_errors)


def test_passthrough_class():
    # GIVEN: The passthrough class and a dict of request args
    passthrough_class = jira.resilientsession.PassthroughRetryPrepare()
    my_kwargs = {"nice": "arguments"}
    # WHEN: the dict of request args are prepared
    # THEN: The exact same dict is returned
    assert passthrough_class.prepare(my_kwargs) is my_kwargs


@patch("requests.Session.request")
def test_unspecified_body_remains_unspecified(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0)
    # Data is not specified here.
    session.get(url="mocked_url")
    kwargs = mocked_request_method.call_args.kwargs
    assert "data" not in kwargs


@patch("requests.Session.request")
def test_nonempty_body_is_forwarded(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0)
    session.get(url="mocked_url", data={"some": "fake-data"})
    kwargs = mocked_request_method.call_args.kwargs
    assert kwargs["data"] == '{"some": "fake-data"}'


@patch("requests.Session.request")
def test_with_requests_simple_timeout(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0, timeout=1)
    session.get(url="mocked_url", data={"some": "fake-data"})
    kwargs = mocked_request_method.call_args.kwargs
    assert kwargs["data"] == '{"some": "fake-data"}'


@patch("requests.Session.request")
def test_with_requests_tuple_timeout(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0, timeout=(1, 3.5))
    session.get(url="mocked_url", data={"some": "fake-data"})
    kwargs = mocked_request_method.call_args.kwargs
    assert kwargs["data"] == '{"some": "fake-data"}'


@patch("requests.Session.request")
def test_verify_is_forwarded(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0)

    session.get(url="mocked_url", data={"some": "fake-data"})
    kwargs = mocked_request_method.call_args.kwargs
    assert kwargs["verify"] == session.verify is True

    session.verify = False
    session.get(url="mocked_url", data={"some": "fake-data"})
    kwargs = mocked_request_method.call_args.kwargs
    assert kwargs["verify"] == session.verify is False


@patch("requests.Session.request")
def test_empty_dict_body_not_forwarded(mocked_request_method: Mock):
    # Disable retries for this test.
    session = jira.resilientsession.ResilientSession(max_retries=0)
    # Empty dictionary should not be converted to JSON
    session.get(url="mocked_url", data={})
    kwargs = mocked_request_method.call_args.kwargs
    assert "data" not in kwargs
