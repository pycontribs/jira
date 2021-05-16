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
