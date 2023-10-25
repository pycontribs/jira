from __future__ import annotations

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
