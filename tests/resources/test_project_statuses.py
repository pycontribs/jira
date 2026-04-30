from __future__ import annotations

from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class ProjectStatusesByIssueTypeTests(JiraTestCase):
    def test_issue_types_for_project(self):
        issue_types = self.jira.issue_types_for_project(self.project_a)

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
            self_status_id = self.jira.status(status.id).id
            self.assertEqual(self_status_id, status.id)
            self_status_name = self.jira.status(status.name).name
            self.assertEqual(self_status_name, status.name)
