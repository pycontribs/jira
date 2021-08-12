from tests.conftest import JiraTestCase


class WorklogTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

    def test_worklogs(self):
        worklog = self.jira.add_worklog(self.issue_1, "2h")
        worklogs = self.jira.worklogs(self.issue_1)
        self.assertEqual(len(worklogs), 1)
        worklog.delete()

    def test_worklogs_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        worklog = self.jira.add_worklog(issue, "2h")
        worklogs = self.jira.worklogs(issue)
        self.assertEqual(len(worklogs), 1)
        worklog.delete()

    def test_worklog(self):
        worklog = self.jira.add_worklog(self.issue_1, "1d 2h")
        new_worklog = self.jira.worklog(self.issue_1, str(worklog))
        self.assertEqual(new_worklog.author.name, self.test_manager.user_admin.name)
        self.assertEqual(new_worklog.timeSpent, "1d 2h")
        worklog.delete()

    def test_worklog_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        worklog = self.jira.add_worklog(issue, "1d 2h")
        new_worklog = self.jira.worklog(issue, str(worklog))
        self.assertEqual(new_worklog.author.name, self.test_manager.user_admin.name)
        self.assertEqual(new_worklog.timeSpent, "1d 2h")
        worklog.delete()

    def test_add_worklog(self):
        worklog_count = len(self.jira.worklogs(self.issue_2))
        worklog = self.jira.add_worklog(self.issue_2, "2h")
        self.assertIsNotNone(worklog)
        self.assertEqual(len(self.jira.worklogs(self.issue_2)), worklog_count + 1)
        worklog.delete()

    def test_add_worklog_with_issue_obj(self):
        issue = self.jira.issue(self.issue_2)
        worklog_count = len(self.jira.worklogs(issue))
        worklog = self.jira.add_worklog(issue, "2h")
        self.assertIsNotNone(worklog)
        self.assertEqual(len(self.jira.worklogs(issue)), worklog_count + 1)
        worklog.delete()

    def test_update_and_delete_worklog(self):
        worklog = self.jira.add_worklog(self.issue_3, "3h")
        issue = self.jira.issue(self.issue_3, fields="worklog,timetracking")
        worklog.update(comment="Updated!", timeSpent="2h")
        self.assertEqual(worklog.comment, "Updated!")
        # rem_estimate = issue.fields.timetracking.remainingEstimate
        self.assertEqual(worklog.timeSpent, "2h")
        issue = self.jira.issue(self.issue_3, fields="worklog,timetracking")
        self.assertEqual(issue.fields.timetracking.remainingEstimate, "1h")
        worklog.delete()
        issue = self.jira.issue(self.issue_3, fields="worklog,timetracking")
        self.assertEqual(issue.fields.timetracking.remainingEstimate, "3h")
