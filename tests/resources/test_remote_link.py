from jira.exceptions import JIRAError
from tests.conftest import JiraTestCase, broken_test


@broken_test(reason="Nothing from remote link works")
class RemoteLinkTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

    def test_remote_links(self):
        self.jira.add_remote_link(
            "ZTRAVISDEB-3", globalId="python-test:story.of.horse.riding"
        )
        links = self.jira.remote_links("QA-44")
        self.assertEqual(len(links), 1)
        links = self.jira.remote_links("BULK-1")
        self.assertEqual(len(links), 0)

    @broken_test(reason="temporary disabled")
    def test_remote_links_with_issue_obj(self):
        issue = self.jira.issue("QA-44")
        links = self.jira.remote_links(issue)
        self.assertEqual(len(links), 1)
        issue = self.jira.issue("BULK-1")
        links = self.jira.remote_links(issue)
        self.assertEqual(len(links), 0)

    @broken_test(reason="temporary disabled")
    def test_remote_link(self):
        link = self.jira.remote_link("QA-44", "10000")
        self.assertEqual(link.id, 10000)
        self.assertTrue(hasattr(link, "globalId"))
        self.assertTrue(hasattr(link, "relationship"))

    @broken_test(reason="temporary disabled")
    def test_remote_link_with_issue_obj(self):
        issue = self.jira.issue("QA-44")
        link = self.jira.remote_link(issue, "10000")
        self.assertEqual(link.id, 10000)
        self.assertTrue(hasattr(link, "globalId"))
        self.assertTrue(hasattr(link, "relationship"))

    @broken_test(reason="temporary disabled")
    def test_add_remote_link(self):
        link = self.jira.add_remote_link(
            "BULK-3",
            globalId="python-test:story.of.horse.riding",
            object={"url": "http://google.com", "title": "googlicious!"},
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link("BULK-3", link.id)
        self.assertEqual(link.application.name, "far too silly")
        self.assertEqual(link.application.type, "sketch")
        self.assertEqual(link.object.url, "http://google.com")
        self.assertEqual(link.object.title, "googlicious!")
        self.assertEqual(link.relationship, "mousebending")
        self.assertEqual(link.globalId, "python-test:story.of.horse.riding")

    @broken_test(reason="temporary disabled")
    def test_add_remote_link_with_issue_obj(self):
        issue = self.jira.issue("BULK-3")
        link = self.jira.add_remote_link(
            issue,
            globalId="python-test:story.of.horse.riding",
            object={"url": "http://google.com", "title": "googlicious!"},
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link(issue, link.id)
        self.assertEqual(link.application.name, "far too silly")
        self.assertEqual(link.application.type, "sketch")
        self.assertEqual(link.object.url, "http://google.com")
        self.assertEqual(link.object.title, "googlicious!")
        self.assertEqual(link.relationship, "mousebending")
        self.assertEqual(link.globalId, "python-test:story.of.horse.riding")

    @broken_test(reason="temporary disabled")
    def test_update_remote_link(self):
        link = self.jira.add_remote_link(
            "BULK-3",
            globalId="python-test:story.of.horse.riding",
            object={"url": "http://google.com", "title": "googlicious!"},
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        # creation response doesn't include full remote link info,
        #  so we fetch it again using the new internal ID
        link = self.jira.remote_link("BULK-3", link.id)
        link.update(
            object={"url": "http://yahoo.com", "title": "yahoo stuff"},
            globalId="python-test:updated.id",
            relationship="cheesing",
        )
        self.assertEqual(link.globalId, "python-test:updated.id")
        self.assertEqual(link.relationship, "cheesing")
        self.assertEqual(link.object.url, "http://yahoo.com")
        self.assertEqual(link.object.title, "yahoo stuff")
        link.delete()

    @broken_test(reason="temporary disabled")
    def test_delete_remove_link(self):
        link = self.jira.add_remote_link(
            "BULK-3",
            globalId="python-test:story.of.horse.riding",
            object={"url": "http://google.com", "title": "googlicious!"},
            application={"name": "far too silly", "type": "sketch"},
            relationship="mousebending",
        )
        _id = link.id
        link.delete()
        self.assertRaises(JIRAError, self.jira.remote_link, "BULK-3", _id)
