import pytest
from tests import JiraTestManager


@pytest.fixture(scope='session')
def test_manager():
    return JiraTestManager()


@pytest.fixture()
def jira_admin(test_manager):
    return test_manager.jira_admin


@pytest.fixture()
def jira_normal(test_manager):
    return test_manager.jira_normal
