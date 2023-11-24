from __future__ import annotations

from tests.conftest import jira_svcTestCase


class IssuePropertyTests(jira_svcTestCase):
    def setUp(self):
        jira_svcTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1

    def test_issue_property(self):
        self.jira_svc.add_issue_property(
            self.issue_1, "custom-property", "Testing a property value"
        )
        properties = self.jira_svc.issue_properties(self.issue_1)
        self.assertEqual(len(properties), 1)

        prop = self.jira_svc.issue_property(self.issue_1, "custom-property")
        self.assertEqual(prop.key, "custom-property")
        self.assertEqual(prop.value, "Testing a property value")
        prop.delete()
        properties = self.jira_svc.issue_properties(self.issue_1)
        self.assertEqual(len(properties), 0)
