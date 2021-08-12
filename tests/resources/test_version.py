from jira.exceptions import JIRAError
from tests.conftest import JiraTestCase


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
