from __future__ import annotations

from tests.conftest import jira_svcTestCase, allow_on_cloud


@allow_on_cloud
class GroupsTest(jira_svcTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.group_name = (
            "administrators" if self.is_jira_svc_cloud_ci else "jira_svc-administrators"
        )

    def test_group(self):
        group = self.jira_svc.group(self.group_name)
        self.assertEqual(group.name, self.group_name)

    def test_groups(self):
        groups = self.jira_svc.groups()
        self.assertGreater(len(groups), 0)

    def test_groups_for_users(self):
        groups = self.jira_svc.groups(self.group_name)
        self.assertGreater(len(groups), 0)
