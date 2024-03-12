from __future__ import annotations

import logging
from unittest import TestCase

import pytest

from jira.exceptions import JIRAError
from jira.utils import cloud, experimental

LOG = logging.getLogger("test_logger")
LOG.addHandler(logging.StreamHandler())


class MockClient:
    def __init__(self, is_cloud=False):
        self.is_cloud = is_cloud
        self.log = LOG

    @property
    def _is_cloud(self):
        return self.is_cloud

    @cloud
    def mock_method(self, *args, **kwargs):
        return (args, kwargs)

    @experimental
    def mock_method_raises_jira_error(self, *args, **kwargs):
        raise JIRAError(**kwargs)


class MockResponse:
    def __init__(self, status_code=404):
        self.status_code = status_code
        self.url = "some/url/that/does/not/exist"


class UtilsTests(TestCase):
    def setUp(self):
        self.mock_client = MockClient
        self.mock_response = MockResponse

    @pytest.fixture(autouse=True)
    def caplog(self, caplog):
        self.caplog = caplog

    def test_not_cloud(self):
        mock_client = self.mock_client()
        mock_client.mock_method()
        self.assertEqual(
            self.caplog.messages[0],
            "This functionality is not available on Jira Data Center (Server) version.",
        )

    def test_cloud(self):
        mock_client = self.mock_client(is_cloud=True)
        out = mock_client.mock_method("one", two="three")
        self.assertIsNotNone(out)

    def test_experimental_404(self):
        mock_response = self.mock_response()
        response = self.mock_client().mock_method_raises_jira_error(
            response=mock_response,
            request=mock_response,
            status_code=mock_response.status_code,
        )
        self.assertIsNone(response)
        self.assertEqual(
            self.caplog.messages[0],
            f"Functionality at path {mock_response.url} is/was experimental. Status Code: "
            f"{mock_response.status_code}",
        )

    def test_experimental_405(self):
        mock_response = self.mock_response(status_code=405)
        response = self.mock_client().mock_method_raises_jira_error(
            response=mock_response,
            request=mock_response,
            status_code=mock_response.status_code,
        )
        self.assertIsNone(response)
        self.assertEqual(
            self.caplog.messages[0],
            f"Functionality at path {mock_response.url} is/was experimental. Status Code: "
            f"{mock_response.status_code}",
        )

    def test_experimental_non_200_not_404_405(self):
        status_code = 400
        mock_response = self.mock_response(status_code=status_code)

        with pytest.raises(JIRAError) as ex:
            self.mock_client().mock_method_raises_jira_error(
                response=mock_response,
                request=mock_response,
                status_code=mock_response.status_code,
            )

        self.assertEqual(ex.value.status_code, status_code)
        self.assertIsInstance(ex.value, JIRAError)
