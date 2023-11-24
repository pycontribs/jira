from __future__ import annotations

import pytest

import jira_svc.resources

MOCK_URL = "http://customized-jira_svc.com/rest/"


def url_test_case(example_url: str):
    return f"{MOCK_URL}{example_url}"


class TestResource:
    @pytest.mark.parametrize(
        ["example_url", "expected_class"],
        # fmt: off
        [
            (url_test_case("api/latest/issue/JRA-1330"), jira_svc.resources.Issue),
            (url_test_case("api/latest/project/BULK"), jira_svc.resources.Project),
            (url_test_case("api/latest/project/IMG/role/10002"), jira_svc.resources.Role),
            (url_test_case("plugin-resource/4.5/json/getMyObject"), jira_svc.resources.UnknownResource),
            (url_test_case("group?groupname=bla"), jira_svc.resources.Group),
            (url_test_case("user?username=bla"), jira_svc.resources.User),  # jira_svc Server / Data Center
            (url_test_case("user?accountId=bla"), jira_svc.resources.User),  # jira_svc Cloud
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
        assert jira_svc.resources.cls_for_resource(example_url) == expected_class
