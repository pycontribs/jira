from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from requests import Response
from requests.structures import CaseInsensitiveDict

from jira_svc.exceptions import jira_svcError

DUMMY_HEADERS = {"h": "nice headers"}
DUMMY_TEXT = "nice text"
DUMMY_URL = "https://nice.jira_svc.tests"
DUMMY_STATUS_CODE = 200

PATCH_BASE = "jira_svc.exceptions"


class ExceptionsTests(unittest.TestCase):
    class MockResponse(Response):
        def __init__(
            self,
            headers: dict = None,
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
            headers: dict = None,
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

    def test_jira_svc_error_response_added(self):
        err = jira_svcError(
            response=self.MockResponse(headers=DUMMY_HEADERS, text=DUMMY_TEXT)
        )
        err_str = str(err)

        assert f"headers = {DUMMY_HEADERS}" in err_str
        assert f"text = {DUMMY_TEXT}" in err_str

    def test_jira_svc_error_malformed_response(self):
        # GIVEN: a malformed Response object, without headers or text set
        bad_repsonse = self.MalformedMockResponse()
        # WHEN: The jira_svcError's __str__ method is called
        err = jira_svcError(response=bad_repsonse)
        err_str = str(err)
        # THEN: there are no errors and neither headers nor text are in the result
        assert "headers = " not in err_str
        assert "text = " not in err_str

    def test_jira_svc_error_request_added(self):
        err = jira_svcError(
            request=self.MockResponse(headers=DUMMY_HEADERS, text=DUMMY_TEXT)
        )
        err_str = str(err)

        assert f"headers = {DUMMY_HEADERS}" in err_str
        assert f"text = {DUMMY_TEXT}" in err_str

    def test_jira_svc_error_malformed_request(self):
        # GIVEN: a malformed Response object, without headers or text set
        bad_repsonse = self.MalformedMockResponse()
        # WHEN: The jira_svcError's __str__ method is called
        err = jira_svcError(request=bad_repsonse)
        err_str = str(err)
        # THEN: there are no errors and neither headers nor text are in the result
        assert "headers = " not in err_str
        assert "text = " not in err_str

    def test_jira_svc_error_url_added(self):
        assert f"url: {DUMMY_URL}" in str(jira_svcError(url=DUMMY_URL))

    def test_jira_svc_error_status_code_added(self):
        assert f"jira_svcError HTTP {DUMMY_STATUS_CODE}" in str(
            jira_svcError(status_code=DUMMY_STATUS_CODE)
        )

    def test_jira_svc_error_text_added(self):
        dummy_text = "wow\tthis\nis\nso cool"
        assert f"text: {dummy_text}" in str(jira_svcError(text=dummy_text))

    def test_jira_svc_error_log_to_tempfile_if_env_var_set(self):
        # GIVEN: the right env vars are set and the tempfile's filename
        env_vars = {"PYjira_svc_LOG_TO_TEMPFILE": "so true"}
        test_jira_svc_error_filename = (
            Path(__file__).parent / "test_jira_svc_error_log_to_tempfile.bak"
        )
        # https://docs.python.org/3/library/unittest.mock.html#mock-open
        mocked_open = mock_open()

        # WHEN: a jira_svcError's __str__ method is called and
        # log details are expected to be sent to the tempfile
        with patch.dict("os.environ", env_vars), patch(
            f"{PATCH_BASE}.tempfile.mkstemp", autospec=True
        ) as mock_mkstemp, patch(f"{PATCH_BASE}.open", mocked_open):
            mock_mkstemp.return_value = 0, str(test_jira_svc_error_filename)
            str(jira_svcError(response=self.MockResponse(text=DUMMY_TEXT)))

        # THEN: the known filename is opened and contains the exception details
        mocked_open.assert_called_once_with(str(test_jira_svc_error_filename), "w")
        mock_file_stream = mocked_open()
        assert f"text = {DUMMY_TEXT}" in mock_file_stream.write.call_args[0][0]

    def test_jira_svc_error_log_to_tempfile_not_used_if_env_var_not_set(self):
        # GIVEN: no env vars are set and the tempfile's filename
        env_vars = {}
        test_jira_svc_error_filename = (
            Path(__file__).parent / "test_jira_svc_error_log_to_tempfile.bak"
        )
        # https://docs.python.org/3/library/unittest.mock.html#mock-open
        mocked_open = mock_open()

        # WHEN: a jira_svcError's __str__ method is called
        with patch.dict("os.environ", env_vars), patch(
            f"{PATCH_BASE}.tempfile.mkstemp", autospec=True
        ) as mock_mkstemp, patch(f"{PATCH_BASE}.open", mocked_open):
            mock_mkstemp.return_value = 0, str(test_jira_svc_error_filename)
            str(jira_svcError(response=self.MockResponse(text=DUMMY_TEXT)))

        # THEN: no files are opened
        mocked_open.assert_not_called()
