from __future__ import annotations

from jira.resources import IssueType
from tests.conftest import JiraTestCase, allow_on_cloud


class IssueTypeTest(JiraTestCase):
    def setUp(self) -> None:
        super().setUp()

    @allow_on_cloud
    def test_issue_type(self):
        issue_types = self.test_manager.jira_admin.project_issue_types(
            project=self.project_a
        )
        assert isinstance(issue_types[0], IssueType)

    @allow_on_cloud
    def test_issue_type_pagination(self):
        issue_types = self.test_manager.jira_admin.project_issue_types(
            project=self.project_a, startAt=50
        )
        assert len(issue_types) == 0
