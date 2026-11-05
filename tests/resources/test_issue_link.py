from __future__ import annotations

import logging
from unittest import mock

import pytest

import jira.client
from jira.resources import IssueLinkType
from tests.conftest import JiraTestCase


class IssueLinkTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.link_types = self.test_manager.jira_admin.issue_link_types()

    def test_issue_link(self):
        self.link = self.test_manager.jira_admin.issue_link_type(self.link_types[0].id)
        link = self.link  # Duplicate outward
        self.assertEqual(link.id, self.link_types[0].id)

    def test_create_issue_link(self):
        self.test_manager.jira_admin.create_issue_link(
            self.link_types[0].outward,
            self.test_manager.project_b_issue1,
            self.test_manager.project_b_issue2,
        )

    def test_create_issue_link_with_issue_link_obj(self):
        self.test_manager.jira_admin.create_issue_link(
            self.link_types[0],
            self.test_manager.project_b_issue1,
            self.test_manager.project_b_issue2,
        )

    def test_create_issue_link_with_issue_obj(self):
        inwardissue = self.test_manager.jira_admin.issue(
            self.test_manager.project_b_issue1
        )
        self.assertIsNotNone(inwardissue)
        outwardissue = self.test_manager.jira_admin.issue(
            self.test_manager.project_b_issue2
        )
        self.assertIsNotNone(outwardissue)
        self.test_manager.jira_admin.create_issue_link(
            self.link_types[0].outward, inwardissue, outwardissue
        )

        # @unittest.skip("Creating an issue link doesn't return its ID, so can't easily test delete")
        # def test_delete_issue_link(self):
        #    pass

    def test_issue_link_type(self):
        link_type = self.test_manager.jira_admin.issue_link_type(self.link_types[0].id)
        self.assertEqual(link_type.id, self.link_types[0].id)
        self.assertEqual(link_type.name, self.link_types[0].name)


def _link_type(client, name, inward, outward, id):
    raw = {"id": id, "name": name, "inward": inward, "outward": outward}
    return IssueLinkType(client._options, client._session, raw=raw)


@pytest.fixture()
def link_client(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.post("https://jira.example.com/rest/api/2/issueLink", status_code=201)
    link_types = [
        _link_type(client, "Problem/Incident", "Duplicate", "causes", "1"),
        _link_type(client, "Duplicate", "is duplicated by", "duplicates", "2"),
    ]
    with mock.patch.object(client, "issue_link_types", return_value=link_types):
        yield client, link_types


@pytest.mark.parametrize(
    "type_arg,expected_id,inward,outward",
    [
        ("Duplicate", "2", "A-1", "B-1"),
        ("duplicates", "2", "A-1", "B-1"),
        ("is duplicated by", "2", "B-1", "A-1"),
        ("causes", "1", "A-1", "B-1"),
    ],
)
def test_create_issue_link_resolves_type(
    link_client, requests_mock, type_arg, expected_id, inward, outward
):
    client, _ = link_client

    client.create_issue_link(type_arg, "A-1", "B-1")

    body = requests_mock.last_request.json()
    assert body["type"]["id"] == expected_id
    assert body["inwardIssue"] == {"key": inward}
    assert body["outwardIssue"] == {"key": outward}


@pytest.mark.parametrize("as_keyword", [False, True])
def test_create_issue_link_accepts_issue_link_type(
    link_client, requests_mock, caplog, as_keyword
):
    client, link_types = link_client

    if as_keyword:
        client.create_issue_link(
            type=link_types[1], inwardIssue="A-1", outwardIssue="B-1"
        )
    else:
        client.create_issue_link(link_types[1], "A-1", "B-1")

    body = requests_mock.last_request.json()
    assert body["type"]["name"] == "Duplicate"
    assert body["inwardIssue"] == {"key": "A-1"}
    assert "not present" not in caplog.text


def test_create_issue_link_warns_on_unknown_type(link_client, requests_mock, caplog):
    client, _ = link_client

    with caplog.at_level(logging.WARNING):
        client.create_issue_link("Clones", "A-1", "B-1")

    assert requests_mock.last_request.json()["type"] == {"name": "Clones"}
    assert "Clones" in caplog.text
