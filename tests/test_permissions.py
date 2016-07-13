import pytest


@pytest.fixture
def td(test_manager):
    return {
        'project_a': test_manager.project_a,
        'project_a_id': test_manager.project_a_id,
        'issue_1': test_manager.project_b_issue1,
    }


def test_my_permissions(jira_normal, td):
    perms = jira_normal.my_permissions()

    assert len(perms['permissions']) >= 40


def test_my_permissions_by_project(jira_normal, td):
    perms = jira_normal.my_permissions(projectKey=td['project_a'])

    assert len(perms['permissions']) >= 10

    perms = jira_normal.my_permissions(projectId=td['project_a_id'])

    assert len(perms['permissions']) >= 10


@pytest.mark.skipif(True, reason="broken")
def test_my_permissions_by_issue(jira_normal, td):
    perms = jira_normal.my_permissions(issueKey='ZTRAVISDEB-7')

    assert len(perms['permissions']) >= 10

    perms = jira_normal.my_permissions(issueId='11021')

    assert len(perms['permissions']) >= 10
