from __future__ import annotations

from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class IssuePropertyTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1

    def test_issue_property(self):
        self.jira.add_issue_property(
            self.issue_1, "custom-property", "Testing a property value"
        )
        properties = self.jira.issue_properties(self.issue_1)
        self.assertEqual(len(properties), 1)

        prop = self.jira.issue_property(self.issue_1, "custom-property")
        self.assertEqual(prop.key, "custom-property")
        self.assertEqual(prop.value, "Testing a property value")
        prop.delete()
        if not self.jira._is_cloud:
            properties = self.jira.issue_properties(self.issue_1)
            self.assertEqual(len(properties), 0)
