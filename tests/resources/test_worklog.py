from __future__ import annotations

import pytest

import jira.client
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

    def test_add_worklog_with_properties_on_server(self):
        properties = [{"key": "billable", "value": {"approved": True}}]

        with self.assertWarnsRegex(UserWarning, "'properties' argument"):
            worklog = self.jira.add_worklog(self.issue_2, "2h", properties=properties)
        self.addCleanup(worklog.delete)

        self.assertEqual(self.jira.worklog(self.issue_2, worklog.id).timeSpent, "2h")

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


def test_worklogs_and_worklog_send_expand(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    base = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    worklog = {"id": "100", "self": f"{base}/100"}
    requests_mock.get(base, json={"worklogs": [worklog]})
    requests_mock.get(f"{base}/100", json=worklog)

    client.worklogs("ABC-1", expand="properties")
    client.worklog("ABC-1", "100", expand="properties")

    assert [r.qs for r in requests_mock.request_history] == [
        {"expand": ["properties"]},
        {"expand": ["properties"]},
    ]


@pytest.mark.parametrize("notify,expected", [(False, True), (True, False)])
def test_add_worklog_notify(requests_mock, notify, expected):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    requests_mock.post(url, json={"id": "100", "self": f"{url}/100"})

    client.add_worklog("ABC-1", timeSpent="1h", notify=notify)

    assert ("notifyUsers=false" in requests_mock.last_request.url) is expected


def test_add_worklog_sends_properties_on_cloud(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client.deploymentType = "Cloud"
    url = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    requests_mock.post(url, json={"id": "100", "self": f"{url}/100"})
    properties = [{"key": "billable", "value": {"approved": True}}]

    client.add_worklog("ABC-1", timeSpent="1h", properties=properties)

    assert requests_mock.last_request.json() == {
        "timeSpent": "1h",
        "properties": properties,
    }


def test_add_worklog_warns_and_leaves_out_properties_on_server(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    requests_mock.post(url, json={"id": "100", "self": f"{url}/100"})
    properties = [{"key": "billable", "value": {"approved": True}}]

    with pytest.warns(UserWarning, match="'properties' argument") as warned:
        client.add_worklog("ABC-1", timeSpent="1h", properties=properties)

    assert warned[0].filename == __file__
    assert requests_mock.last_request.json() == {"timeSpent": "1h"}
