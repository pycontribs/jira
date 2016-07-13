import pytest


@pytest.fixture
def td(test_manager):
    return {
        'project_b': test_manager.project_b,
        'issue': test_manager.project_b_issue1
    }


def test_search_issues(jira_admin, td):
    issues = jira_admin.search_issues('project=%s' % td['project_b'])

    assert len(issues) == 3
    for issue in issues:
        assert issue.key.startswith(td['project_b'])


def test_search_issues_maxresults(jira_admin, td):
    issues = jira_admin.search_issues(
        'project=%s' % td['project_b'], maxResults=10)

    assert len(issues) <= 10


def test_search_issues_startat(jira_admin, td):
    issues = jira_admin.search_issues(
        'project=%s' % td['project_b'], startAt=5770, maxResults=500)
    assert len(issues) <= 500


def test_search_issues_field_limiting(jira_admin, td):
    issues = jira_admin.search_issues(
        'key=%s' % td['issue'], fields='summary,comment')

    assert hasattr(issues[0].fields, 'summary') is True
    assert hasattr(issues[0].fields, 'comment') is True
    assert hasattr(issues[0].fields, 'reporter') is False
    assert hasattr(issues[0].fields, 'progress') is False


def test_search_issues_expandos(jira_admin, td):
    issues = jira_admin.search_issues(
        'key=%s' % td['issue'], expand='changelog')

    # assert hasattr(issues[0], 'names') is True
    assert len(issues) == 1
    assert hasattr(issues[0], 'editmeta') is False
    assert hasattr(issues[0], 'changelog') is True
    assert issues[0].key == td['issue']
