from jira.exceptions import JIRAError
from tests.conftest import JiraTestCase


class RemoteLinkTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3
        self.project_b_issue1_obj = self.test_manager.project_b_issue1_obj

    def test_remote_links(self):
        self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
        )
        links = self.jira.remote_links(self.issue_1)
        self.assertEqual(len(links), 1)
        self.jira.remote_link(self.issue_1, links[0].id).delete()
        links = self.jira.remote_links(self.issue_2)
        self.assertEqual(len(links), 0)

    def test_remote_links_with_issue_obj(self):
        self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
        )
        links = self.jira.remote_links(self.project_b_issue1_obj)
        self.assertEqual(len(links), 1)
        self.jira.remote_link(self.issue_1, links[0].id).delete()
        links = self.jira.remote_links(self.project_b_issue1_obj)
        self.assertEqual(len(links), 0)

    def test_remote_link(self):
        added_link = self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
        )
        link = self.jira.remote_link(self.issue_1, added_link.id)
        self.assertEqual(link.id, added_link.id)
        self.assertTrue(hasattr(link, "application"))
        self.assertTrue(hasattr(link, "object"))

        link.delete()

    def test_remote_link_with_issue_obj(self):
        added_link = self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
        )
        link = self.jira.remote_link(self.project_b_issue1_obj, added_link.id)
        self.assertEqual(link.id, added_link.id)
        self.assertTrue(hasattr(link, "application"))
        self.assertTrue(hasattr(link, "object"))

        link.delete()

    def test_add_remote_link(self):
        link = self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
            globalId="python-test:story.of.horse.riding",
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link(self.issue_1, link.id)
        self.assertEqual(link.object.url, "http://google.com")
        self.assertEqual(link.object.title, "googlicious!")

        link.delete()

    def test_add_remote_link_with_issue_obj(self):
        link = self.jira.add_remote_link(
            self.project_b_issue1_obj,
            object={"url": "http://google.com", "title": "googlicious!"},
            globalId="python-test:story.of.horse.riding",
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link(self.project_b_issue1_obj, link.id)
        self.assertEqual(link.object.url, "http://google.com")
        self.assertEqual(link.object.title, "googlicious!")

        link.delete()

    def test_update_remote_link(self):
        link = self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
            globalId="python-test:story.of.horse.riding",
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link(self.issue_1, link.id)
        link.update(
            object={"url": "http://yahoo.com", "title": "yahoo stuff"},
            globalId="python-test:updated.id",
            relationship="cheesing",
        )
        self.assertEqual(link.object.url, "http://yahoo.com")
        self.assertEqual(link.object.title, "yahoo stuff")
        link.delete()

    def test_delete_remote_link(self):
        link = self.jira.add_remote_link(
            self.issue_1,
            object={"url": "http://google.com", "title": "googlicious!"},
            globalId="python-test:story.of.horse.riding",
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        _id = link.id
        link = self.jira.remote_link(self.issue_1, link.id)
        link.delete()
        self.assertRaises(JIRAError, self.jira.remote_link, self.issue_1, _id)
