import pytest
from tests import rndstr


@pytest.fixture(scope="module")
def td(test_manager):
    """
    Test data for this module
    """
    return {
        'project_b': test_manager.project_b,
        'issue_1': test_manager.project_b_issue1,
        'issue_2': test_manager.project_b_issue2,
        'CI_JIRA_ADMIN': test_manager.CI_JIRA_ADMIN
    }


def test_filter(jira_admin, td):
    jql = "project = %s and component is not empty" % td['project_b']
    name = 'same filter ' + rndstr()
    myfilter = jira_admin.create_filter(
        name=name,
        description="just some new test filter",
        jql=jql,
        favourite=False)

    assert myfilter.name == name
    assert myfilter.owner.name == td['CI_JIRA_ADMIN']

    myfilter.delete()


def test_favourite_filters(jira_admin, td):
    # filters = jira_admin.favourite_filters()
    jql = "project = %s and component is not empty" % td['project_b']
    name = "filter-to-fav-" + rndstr()
    myfilter = jira_admin.create_filter(
        name=name,
        description="just some new test filter",
        jql=jql,
        favourite=True)
    new_filters = jira_admin.favourite_filters()

    assert name in [f.name for f in new_filters]

    myfilter.delete()
