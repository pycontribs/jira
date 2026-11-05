from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import jira.client
from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class GroupsTest(JiraTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.group_name = (
            "administrators" if self.is_jira_cloud_ci else "jira-administrators"
        )

    def test_group(self):
        group = self.jira.group(self.group_name)
        self.assertEqual(group.name, self.group_name)

    def test_groups(self):
        groups = self.jira.groups()
        self.assertGreater(len(groups), 0)

    def test_groups_for_users(self):
        groups = self.jira.groups(self.group_name)
        self.assertGreater(len(groups), 0)


def _group_user(name: str) -> dict:
    return {"name": name, "displayName": name.title(), "active": True}


def test_group_members_expands_users_before_jira_10(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client._version = (9, 12, 0)
    url = "https://jira.example.com/rest/api/2/group"
    requests_mock.get(
        url,
        [
            {
                "json": {
                    "users": {
                        "size": 3,
                        "end-index": 1,
                        "items": [_group_user("alice"), _group_user("bob")],
                    }
                }
            },
            {
                "json": {
                    "users": {
                        "size": 3,
                        "end-index": 2,
                        "items": [_group_user("carol")],
                    }
                }
            },
        ],
    )

    members = client.group_members("devs")

    assert list(members) == ["alice", "bob", "carol"]
    assert [r.qs["expand"] for r in requests_mock.request_history] == [
        ["users"],
        ["users[2:51]"],
    ]


def test_group_members_pages_group_member_on_jira_10(requests_mock):
    """Regression test for https://github.com/pycontribs/jira/issues/891."""
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client._version = (10, 3, 7)
    url = "https://jira.example.com/rest/api/2/group/member"
    requests_mock.get(
        url,
        [
            {
                "json": {
                    "startAt": 0,
                    "maxResults": 2,
                    "isLast": False,
                    "values": [_group_user("alice"), _group_user("bob")],
                }
            },
            {
                "json": {
                    "startAt": 2,
                    "maxResults": 2,
                    "isLast": True,
                    "values": [_group_user("carol")],
                }
            },
        ],
    )

    members = client.group_members("devs")

    assert list(members) == ["alice", "bob", "carol"]
    history = requests_mock.request_history
    assert all(r.path == "/rest/api/2/group/member" for r in history)
    assert [parse_qs(urlsplit(r.url).query) for r in history] == [
        {"groupname": ["devs"]},
        {"groupname": ["devs"], "startAt": ["2"]},
    ]
