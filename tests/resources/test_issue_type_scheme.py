from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from jira import JIRA
from tests.conftest import JiraTestCase, allow_on_cloud

SCHEMES_URL = "https://jira.example.com/rest/api/2/issuetypescheme"


class IssueTypeSchemeTests(JiraTestCase):
    @allow_on_cloud
    def test_issue_type_schemes_with_issue_types(self):
        schemes = self.jira.issue_type_schemes(expand_issue_types=True)

        self.assertGreaterEqual(len(schemes), 1)
        for scheme in schemes:
            self.assertTrue(scheme["id"])
            self.assertTrue(scheme["name"])
        self.assertTrue(any("issueTypes" in scheme for scheme in schemes))


def _client(deployment_type: str) -> JIRA:
    client = JIRA(server="https://jira.example.com", get_server_info=False)
    client.deploymentType = deployment_type
    return client


def _query(request) -> dict[str, list[str]]:
    return parse_qs(urlsplit(request.url).query)


def test_unit_issue_type_schemes_cloud_fetches_every_page(requests_mock):
    pages = {
        "0": {
            "startAt": 0,
            "maxResults": 2,
            "total": 3,
            "isLast": False,
            "values": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        },
        "2": {
            "startAt": 2,
            "maxResults": 2,
            "total": 3,
            "isLast": True,
            "values": [{"id": "3", "name": "C"}],
        },
    }
    requests_mock.get(
        SCHEMES_URL,
        json=lambda request, context: pages[_query(request).get("startAt", ["0"])[0]],
    )

    schemes = _client("Cloud").issue_type_schemes()

    assert schemes == [
        {"id": "1", "name": "A"},
        {"id": "2", "name": "B"},
        {"id": "3", "name": "C"},
    ]
    assert [_query(r).get("startAt") for r in requests_mock.request_history] == [
        None,
        ["2"],
    ]
    assert all("expand" not in _query(r) for r in requests_mock.request_history)


@pytest.mark.parametrize(
    "kwargs,expand",
    [
        ({"expand_projects": True}, "projects"),
        ({"expand_issue_types": True}, "issueTypes"),
        ({"expand_projects": True, "expand_issue_types": True}, "projects,issueTypes"),
    ],
)
def test_unit_issue_type_schemes_cloud_sends_expand(requests_mock, kwargs, expand):
    requests_mock.get(
        SCHEMES_URL,
        json={"startAt": 0, "maxResults": 50, "total": 0, "isLast": True, "values": []},
    )

    assert _client("Cloud").issue_type_schemes(**kwargs) == []

    assert _query(requests_mock.last_request)["expand"] == [expand]


def test_unit_issue_type_schemes_server_reads_schemes(requests_mock):
    schemes = [{"id": "10000", "name": "Default Issue Type Scheme"}]
    requests_mock.get(SCHEMES_URL, json={"schemes": schemes})

    assert _client("Server").issue_type_schemes() == schemes

    assert requests_mock.call_count == 1
    assert _query(requests_mock.last_request) == {}


def test_unit_issue_type_schemes_server_expands_issue_types(requests_mock):
    requests_mock.get(SCHEMES_URL, json={"schemes": []})

    _client("Server").issue_type_schemes(expand_issue_types=True)

    assert _query(requests_mock.last_request) == {"expand": ["schemes.issueTypes"]}


def test_unit_issue_type_schemes_server_warns_on_expand_projects(requests_mock):
    schemes = [{"id": "10000", "name": "Default Issue Type Scheme"}]
    requests_mock.get(SCHEMES_URL, json={"schemes": schemes})

    with pytest.warns(UserWarning, match="expand_projects") as warned:
        result = _client("Server").issue_type_schemes(expand_projects=True)

    assert result == schemes
    assert warned[0].filename == __file__
    assert _query(requests_mock.last_request) == {}
