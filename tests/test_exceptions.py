from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from requests import Request, Response
from requests.structures import CaseInsensitiveDict

from jira.exceptions import JIRAError
from jira.resilientsession import raise_on_error

pytestmark = pytest.mark.unit

DUMMY_HEADERS = {"h": "nice headers"}
DUMMY_TEXT = "nice text"
DUMMY_URL = "https://nice.jira.tests"
DUMMY_STATUS_CODE = 200

PATCH_BASE = "jira.exceptions"


class ExceptionsTests(unittest.TestCase):
    class MockResponse(Response):
        def __init__(
            self,
            headers: dict | None = None,
            text: str = "",
            status_code: int = DUMMY_STATUS_CODE,
            url: str = DUMMY_URL,
        ):
            """Sub optimal but we create a mock response like this."""
            self.headers = CaseInsensitiveDict(headers if headers else {})
            self._text = text
            self.status_code = status_code
            self.url = url

        @property
        def text(self):
            return self._text

        @text.setter
        def text(self, new_text):
            self._text = new_text

    class MalformedMockResponse:
        def __init__(
            self,
            headers: dict | None = None,
            text: str = "",
            status_code: int = DUMMY_STATUS_CODE,
            url: str = DUMMY_URL,
        ):
            if headers:
                self.headers = headers
            if text:
                self.text = text
            self.url = url
            self.status_code = status_code

    def test_jira_error_response_added(self):
        err = JIRAError(
            response=self.MockResponse(headers=DUMMY_HEADERS, text=DUMMY_TEXT)
        )
        err_str = str(err)

        assert f"headers = {DUMMY_HEADERS}" in err_str
        assert f"text = {DUMMY_TEXT}" in err_str

    def test_jira_error_malformed_response(self):
        # GIVEN: a malformed Response object, without headers or text set
        bad_response = self.MalformedMockResponse()
        # WHEN: The JiraError's __str__ method is called
        err = JIRAError(response=bad_response)
        err_str = str(err)
        # THEN: there are no errors and neither headers nor text are in the result
        assert "headers = " not in err_str
        assert "text = " not in err_str

    def test_jira_error_request_added(self):
        err = JIRAError(
            request=self.MockResponse(headers=DUMMY_HEADERS, text=DUMMY_TEXT)
        )
        err_str = str(err)

        assert f"headers = {DUMMY_HEADERS}" in err_str
        assert f"text = {DUMMY_TEXT}" in err_str

    def test_jira_error_malformed_request(self):
        # GIVEN: a malformed Response object, without headers or text set
        bad_response = self.MalformedMockResponse()
        # WHEN: The JiraError's __str__ method is called
        err = JIRAError(request=bad_response)
        err_str = str(err)
        # THEN: there are no errors and neither headers nor text are in the result
        assert "headers = " not in err_str
        assert "text = " not in err_str

    def test_jira_error_url_added(self):
        assert f"url: {DUMMY_URL}" in str(JIRAError(url=DUMMY_URL))

    def test_jira_error_status_code_added(self):
        assert f"JiraError HTTP {DUMMY_STATUS_CODE}" in str(
            JIRAError(status_code=DUMMY_STATUS_CODE)
        )

    def test_jira_error_text_added(self):
        dummy_text = "wow\tthis\nis\nso cool"
        assert f"text: {dummy_text}" in str(JIRAError(text=dummy_text))

    def test_jira_error_log_to_tempfile_if_env_var_set(self):
        # GIVEN: the right env vars are set and the tempfile's filename
        env_vars = {"PYJIRA_LOG_TO_TEMPFILE": "so true"}
        test_unit_jira_error_filename = (
            Path(__file__).parent / "test_unit_jira_error_log_to_tempfile.bak"
        )
        # https://docs.python.org/3/library/unittest.mock.html#mock-open
        mocked_open = mock_open()

        # WHEN: a JIRAError's __str__ method is called and
        # log details are expected to be sent to the tempfile
        with (
            patch.dict("os.environ", env_vars),
            patch(f"{PATCH_BASE}.tempfile.mkstemp", autospec=True) as mock_mkstemp,
            patch(f"{PATCH_BASE}.open", mocked_open),
        ):
            mock_mkstemp.return_value = 0, str(test_unit_jira_error_filename)
            str(JIRAError(response=self.MockResponse(text=DUMMY_TEXT)))

        # THEN: the known filename is opened and contains the exception details
        mocked_open.assert_called_once_with(str(test_unit_jira_error_filename), "w")
        mock_file_stream = mocked_open()
        assert f"text = {DUMMY_TEXT}" in mock_file_stream.write.call_args[0][0]

    def test_jira_error_log_to_tempfile_not_used_if_env_var_not_set(self):
        # GIVEN: no env vars are set and the tempfile's filename
        env_vars = {}
        test_unit_jira_error_filename = (
            Path(__file__).parent / "test_unit_jira_error_log_to_tempfile.bak"
        )
        # https://docs.python.org/3/library/unittest.mock.html#mock-open
        mocked_open = mock_open()

        # WHEN: a JIRAError's __str__ method is called
        with (
            patch.dict("os.environ", env_vars),
            patch(f"{PATCH_BASE}.tempfile.mkstemp", autospec=True) as mock_mkstemp,
            patch(f"{PATCH_BASE}.open", mocked_open),
        ):
            mock_mkstemp.return_value = 0, str(test_unit_jira_error_filename)
            str(JIRAError(response=self.MockResponse(text=DUMMY_TEXT)))

        # THEN: no files are opened
        mocked_open.assert_not_called()


SECRET = "s3cr3t-value"


@pytest.mark.parametrize("header", ["Authorization", "Cookie", "Set-Cookie"])
@pytest.mark.parametrize("side", ["request", "response"])
def test_jira_error_redacts_sensitive_headers(header, side):
    headers = {header: f"Bearer {SECRET}", "Content-Type": "application/json"}
    mock = ExceptionsTests.MockResponse(headers=headers)

    err_str = str(JIRAError(**{side: mock}))

    assert SECRET not in err_str
    assert "application/json" in err_str


@pytest.mark.parametrize("key", ["password", "token"])
@pytest.mark.parametrize("side", ["request", "response"])
def test_jira_error_redacts_sensitive_json_body(key, side):
    body = json.dumps({"user": {"name": "bob", key: SECRET}})
    mock = ExceptionsTests.MockResponse(text=body)

    err_str = str(JIRAError(**{side: mock}))

    assert SECRET not in err_str
    assert "bob" in err_str


def test_jira_error_redacts_secrets_written_to_tempfile():
    mocked_open = mock_open()
    response = ExceptionsTests.MockResponse(
        headers={"Set-Cookie": f"session={SECRET}"},
        text=json.dumps({"password": SECRET}),
    )
    request = ExceptionsTests.MockResponse(
        headers={"Authorization": f"Basic {SECRET}"},
        text=json.dumps({"token": SECRET}),
    )

    with (
        patch.dict("os.environ", {"PYJIRA_LOG_TO_TEMPFILE": "1"}),
        patch(f"{PATCH_BASE}.tempfile.mkstemp", autospec=True) as mock_mkstemp,
        patch(f"{PATCH_BASE}.open", mocked_open),
    ):
        mock_mkstemp.return_value = 0, "jiraerror-test.tmp"
        str(JIRAError(request=request, response=response))

    written = mocked_open().write.call_args[0][0]
    assert "request headers" in written
    assert "response text" in written
    assert SECRET not in written


def test_jira_error_keeps_non_ascii_body_text():
    message = "課題の種類が無効です。"
    body = json.dumps({"errorMessages": [message]}, ensure_ascii=False)
    mock = ExceptionsTests.MockResponse(text=body)

    assert message in str(JIRAError(response=mock))


def test_jira_error_keeps_non_ascii_body_text_when_redacting():
    message = "パスワードが違います"
    body = json.dumps({"password": SECRET, "message": message})
    mock = ExceptionsTests.MockResponse(text=body)

    err_str = str(JIRAError(request=mock))

    assert SECRET not in err_str
    assert message in err_str


def test_jira_error_str_survives_deeply_nested_body():
    depth = 5000
    body = '{"a": ' * depth + "1" + "}" * depth
    mock = ExceptionsTests.MockResponse(text=body)

    assert "JiraError HTTP 400" in str(JIRAError(status_code=400, response=mock))


def test_jira_error_redacts_prepared_request_json_body():
    request = Request(
        "POST",
        "https://jira.example.com/rest/api/2/user",
        json={"name": "bob", "password": SECRET},
    ).prepare()
    assert isinstance(request.body, bytes)

    err_str = str(JIRAError(request=request))

    assert "request body" in err_str
    assert "bob" in err_str
    assert SECRET not in err_str


def test_jira_error_redacts_prepared_request_form_body():
    request = Request(
        "POST",
        "https://jira.example.com/login",
        data={"username": "bob", "password": SECRET},
    ).prepare()

    err_str = str(JIRAError(request=request))

    assert "bob" in err_str
    assert SECRET not in err_str


def test_jira_error_handles_undecodable_prepared_request_body():
    request = Request(
        "POST", "https://jira.example.com/attachments", data=b"\xff\xfe\x00binary"
    ).prepare()

    assert "request body" in str(JIRAError(request=request))


@pytest.mark.parametrize(
    "key",
    [
        "accessToken",
        "apiToken",
        "refresh_token",
        "api_key",
        "apiKey",
        "clientSecret",
        "PASSWORD",
        "newPassword",
        "Authorization",
        "sessionCookie",
    ],
)
def test_jira_error_redacts_secret_like_json_keys(key):
    mock = ExceptionsTests.MockResponse(text=json.dumps({"name": "bob", key: SECRET}))

    err_str = str(JIRAError(request=mock))

    assert SECRET not in err_str
    assert "bob" in err_str


@pytest.mark.parametrize("header", ["X-Api-Key", "X-Auth-Token", "Proxy-Authorization"])
def test_jira_error_redacts_secret_like_headers(header):
    mock = ExceptionsTests.MockResponse(headers={header: SECRET, "Accept": "x/y"})

    err_str = str(JIRAError(request=mock))

    assert SECRET not in err_str
    assert "x/y" in err_str


@pytest.mark.parametrize(
    "body",
    [
        f'{{"name": "bob", "accessToken": "{SECRET}"',
        f"name=bob&api_token={SECRET}",
    ],
    ids=["truncated-json", "form"],
)
def test_jira_error_redacts_secret_like_keys_in_non_json_body(body):
    err_str = str(JIRAError(request=ExceptionsTests.MockResponse(text=body)))

    assert SECRET not in err_str
    assert "bob" in err_str


def test_jira_error_redacts_stored_request_headers():
    headers = CaseInsensitiveDict(
        {"Authorization": f"Bearer {SECRET}", "Accept": "application/json"}
    )

    err = JIRAError(status_code=401, headers=headers)

    assert err.headers["authorization"] == "********"
    assert err.headers["accept"] == "application/json"
    assert headers["Authorization"] == f"Bearer {SECRET}"


def test_raise_on_error_does_not_store_secret_headers():
    response = Response()
    response.status_code = 401
    response._content = b'{"errorMessages": ["Unauthorized"]}'

    with pytest.raises(JIRAError) as exc_info:
        raise_on_error(response, headers={"Authorization": f"Basic {SECRET}"})

    assert SECRET not in repr(exc_info.value.headers)
