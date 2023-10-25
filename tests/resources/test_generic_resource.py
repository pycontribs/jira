from __future__ import annotations

import pytest

import jira.resources

MOCK_URL = "http://customized-jira.com/rest/"


def url_test_case(example_url: str):
    return f"{MOCK_URL}{example_url}"


class TestResource:
    @pytest.mark.parametrize(
        ["example_url", "expected_class"],
        # fmt: off
        [
            (url_test_case("api/latest/issue/JRA-1330"), jira.resources.Issue),
            (url_test_case("api/latest/project/BULK"), jira.resources.Project),
            (url_test_case("api/latest/project/IMG/role/10002"), jira.resources.Role),
            (url_test_case("plugin-resource/4.5/json/getMyObject"), jira.resources.UnknownResource),
            (url_test_case("group?groupname=bla"), jira.resources.Group),
            (url_test_case("user?username=bla"), jira.resources.User),  # Jira Server / Data Center
            (url_test_case("user?accountId=bla"), jira.resources.User),  # Jira Cloud
        ],
        # fmt: on
        ids=[
            "issue",
            "project",
            "role",
            "unknown_resource",
            "group",
            "user",
            "user_cloud",
        ],
    )
    def test_cls_for_resource(self, example_url, expected_class):
        """Test the regex recognizes the right class for a given URL."""
        assert jira.resources.cls_for_resource(example_url) == expected_class
