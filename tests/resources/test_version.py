from __future__ import annotations

from unittest import mock

import pytest

import jira.client
from jira.exceptions import JIRAError
from jira.resources import Version
from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class VersionTests(JiraTestCase):
    def test_create_version(self):
        name = "new version " + self.project_b
        desc = "test version of " + self.project_b
        release_date = "2015-03-11"
        version = self.jira.create_version(
            name, self.project_b, releaseDate=release_date, description=desc
        )
        self.assertEqual(version.name, name)
        self.assertEqual(version.description, desc)
        self.assertEqual(version.releaseDate, release_date)
        version.delete()

    def test_create_version_with_project_obj(self):
        project = self.jira.project(self.project_b)
        version = self.jira.create_version(
            "new version 2",
            project,
            releaseDate="2015-03-11",
            description="test version!",
        )
        self.assertEqual(version.name, "new version 2")
        self.assertEqual(version.description, "test version!")
        self.assertEqual(version.releaseDate, "2015-03-11")
        version.delete()

    def test_update_version(self):
        version = self.jira.create_version(
            "new updated version 1",
            self.project_b,
            releaseDate="2015-03-11",
            description="new to be updated!",
        )
        version.update(name="new updated version name 1", description="new updated!")
        self.assertEqual(version.name, "new updated version name 1")
        self.assertEqual(version.description, "new updated!")

        v = self.jira.version(version.id)
        self.assertEqual(v, version)
        self.assertEqual(v.id, version.id)

        version.delete()

    def test_delete_version(self):
        version_str = "test_delete_version:" + self.test_manager.jid
        version = self.jira.create_version(
            version_str,
            self.project_b,
            releaseDate="2015-03-11",
            description="not long for this world",
        )
        version.delete()
        self.assertRaises(JIRAError, self.jira.version, version.id)


@pytest.mark.unit
class TestVersionOffline:
    def test_create_version_returns_without_sleeping(self, requests_mock, monkeypatch):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        monkeypatch.setattr(
            jira.client.time, "sleep", mock.Mock(side_effect=AssertionError)
        )
        requests_mock.post(
            "https://jira.example.com/rest/api/2/version",
            json={"id": "10000", "name": "1.0", "projectId": 10000},
        )

        version = client.create_version("1.0", "PROJ")

        assert isinstance(version, Version)
        assert version.id == "10000"
        assert requests_mock.last_request.json()["project"] == "PROJ"
