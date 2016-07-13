from tests import not_on_custom_jira_instance


@not_on_custom_jira_instance
def test_dashboards(jira_admin):
    dashboards = jira_admin.dashboards()
    assert len(dashboards) == 3


@not_on_custom_jira_instance
def test_dashboards_filter(jira_admin):
    dashboards = jira_admin.dashboards(filter='my')
    assert len(dashboards) == 2
    assert dashboards[0].id == '10101'


@not_on_custom_jira_instance
def test_dashboards_startat(jira_admin):
    dashboards = jira_admin.dashboards(startAt=1, maxResults=1)
    assert len(dashboards) == 1


@not_on_custom_jira_instance
def test_dashboards_maxresults(jira_admin):
    dashboards = jira_admin.dashboards(maxResults=1)
    assert len(dashboards) == 1


@not_on_custom_jira_instance
def test_dashboard(jira_admin):
    dashboard = jira_admin.dashboard('10101')
    assert dashboard.id == '10101'
    assert dashboard.name == 'Another test dashboard'
