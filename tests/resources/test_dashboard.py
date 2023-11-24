from __future__ import annotations

from tests.conftest import jira_svcTestCase, broken_test


class DashboardTests(jira_svcTestCase):
    def test_dashboards(self):
        dashboards = self.jira_svc.dashboards()
        self.assertGreaterEqual(len(dashboards), 1)

    @broken_test(
        reason="standalone jira_svc docker image has only 1 system dashboard by default"
    )
    def test_dashboards_filter(self):
        dashboards = self.jira_svc.dashboards(filter="my")
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, "10101")

    def test_dashboards_startat(self):
        dashboards = self.jira_svc.dashboards(startAt=0, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxresults(self):
        dashboards = self.jira_svc.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        expected_ds = self.jira_svc.dashboards()[0]
        dashboard = self.jira_svc.dashboard(expected_ds.id)
        self.assertEqual(dashboard.id, expected_ds.id)
        self.assertEqual(dashboard.name, expected_ds.name)
