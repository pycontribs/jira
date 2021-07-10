from tests.conftest import JiraTestCase


class GroupsTest(JiraTestCase):
    def test_group(self):
        group = self.jira.group("jira-administrators")
        self.assertEqual(group.name, "jira-administrators")

    def test_groups(self):
        groups = self.jira.groups()
        self.assertGreater(len(groups), 0)

    def test_groups_for_users(self):
        groups = self.jira.groups("jira-administrators")
        self.assertGreater(len(groups), 0)
