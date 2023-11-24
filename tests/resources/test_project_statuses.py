from __future__ import annotations

from tests.conftest import jira_svcTestCase


class ProjectStatusesByIssueTypeTests(jira_svcTestCase):
    def test_issue_types_for_project(self):
        issue_types = self.jira_svc.issue_types_for_project(self.project_a)

        # should have at least one issue type within the project
        self.assertGreater(len(issue_types), 0)

        # get unique statuses across all issue types
        statuses = []
        for issue_type in issue_types:
            # should have at least one valid status within an issue type by endpoint documentation
            self.assertGreater(len(issue_type.statuses), 0)
            statuses.extend(issue_type.statuses)
        unique_statuses = list(set(statuses))

        # test status id and name for each status within the project
        for status in unique_statuses:
            self_status_id = self.jira_svc.status(status.id).id
            self.assertEqual(self_status_id, status.id)
            self_status_name = self.jira_svc.status(status.name).name
            self.assertEqual(self_status_name, status.name)
