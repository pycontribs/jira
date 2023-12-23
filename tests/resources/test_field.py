from __future__ import annotations

from jira.resources import Field
from tests.conftest import JiraTestCase


class FieldsTest(JiraTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_1_obj = self.test_manager.project_b_issue1_obj

    def test_field(self):
        issue_fields = self.test_manager.jira_admin.project_issue_fields(
            project=self.project_a, issue_type=self.issue_1_obj.fields.issuetype.id
        )
        assert isinstance(issue_fields[0], Field)
