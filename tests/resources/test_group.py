from tests.conftest import JiraTestCase, not_on_custom_jira_instance


@not_on_custom_jira_instance
class GroupsTest(JiraTestCase):
    def test_group(self):
        group = self.jira.group("jira-users")
        self.assertEqual(group.name, "jira-users")

    def test_groups(self):
        groups = self.jira.groups()
        self.assertGreater(len(groups), 0)

    def test_groups_for_users(self):
        groups = self.jira.groups("jira-users")
        self.assertGreater(len(groups), 0)
