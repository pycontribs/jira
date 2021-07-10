from tests.conftest import JiraTestCase, broken_test


class DashboardTests(JiraTestCase):
    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertGreaterEqual(len(dashboards), 1)

    @broken_test(
        reason="standalone jira docker image has only 1 system dashboard by default"
    )
    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter="my")
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, "10101")

    def test_dashboards_startat(self):
        dashboards = self.jira.dashboards(startAt=0, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxresults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        expected_ds = self.jira.dashboards()[0]
        dashboard = self.jira.dashboard(expected_ds.id)
        self.assertEqual(dashboard.id, expected_ds.id)
        self.assertEqual(dashboard.name, expected_ds.name)
