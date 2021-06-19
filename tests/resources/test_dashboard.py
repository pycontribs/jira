from tests.conftest import JiraTestCase, not_on_custom_jira_instance


@not_on_custom_jira_instance
class DashboardTests(JiraTestCase):
    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertEqual(len(dashboards), 3)

    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter="my")
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, "10101")

    def test_dashboards_startat(self):
        dashboards = self.jira.dashboards(startAt=1, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxresults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        dashboard = self.jira.dashboard("10101")
        self.assertEqual(dashboard.id, "10101")
        self.assertEqual(dashboard.name, "Another test dashboard")
