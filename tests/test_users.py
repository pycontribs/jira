import os
import re
import pytest
from tests import not_on_custom_jira_instance
from tests import TEST_ICON_PATH


@pytest.fixture
def td(test_manager):
    return {
        'project_a': test_manager.project_a,
        'project_b': test_manager.project_b,
        'issue': test_manager.project_b_issue3,
        'CI_JIRA_ADMIN': test_manager.CI_JIRA_ADMIN,
        'CI_JIRA_USER': test_manager.CI_JIRA_USER
    }


@not_on_custom_jira_instance
def test_user(jira_admin, td):
    user = jira_admin.user(td['CI_JIRA_ADMIN'])
    assert user.name == td['CI_JIRA_ADMIN']
    assert re.search('.*@example.com', user.emailAddress)


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_projects(jira_admin, td):
    users = jira_admin.search_assignable_users_for_projects(
        td['CI_JIRA_ADMIN'], '%s,%s' % (td['project_a'], td['project_b']))

    assert len(users) >= 1

    usernames = map(lambda user: user.name, users)
    assert td['CI_JIRA_ADMIN'] in usernames


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_projects_maxresults(jira_admin, td):
    users = jira_admin.search_assignable_users_for_projects(
        td['CI_JIRA_ADMIN'], '%s,%s' % (td['project_a'], td['project_b']),
        maxResults=1)
    assert len(users) <= 1


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_projects_startat(jira_admin, td):
    users = jira_admin.search_assignable_users_for_projects(
        td['CI_JIRA_ADMIN'], '%s,%s' % (td['project_a'], td['project_b']),
        startAt=1)
    assert len(users) >= 0


@not_on_custom_jira_instance
def test_search_assignable_users_for_issues_by_project(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_ADMIN'], project=td['project_b'])

    assert len(users) == 1

    usernames = map(lambda user: user.name, users)
    assert td['CI_JIRA_ADMIN'] in usernames


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_issues_by_project_maxresults(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_USER'], project=td['project_b'], maxResults=1)
    assert len(users) <= 1


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_issues_by_project_startat(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_USER'], project=td['project_a'], startAt=1)
    assert len(users) >= 0


@not_on_custom_jira_instance
def test_search_assignable_users_for_issues_by_issue(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_ADMIN'], issueKey=td['issue'])

    assert len(users) == 1

    usernames = map(lambda user: user.name, users)
    assert td['CI_JIRA_ADMIN'] in usernames


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_issues_by_issue_maxresults(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_ADMIN'], issueKey=td['issue'], maxResults=2)
    assert len(users) <= 2


@pytest.mark.xfail(reason='query returns empty list')
def test_search_assignable_users_for_issues_by_issue_startat(jira_admin, td):
    users = jira_admin.search_assignable_users_for_issues(
        td['CI_JIRA_ADMIN'], issueKey=td['issue'], startAt=2)
    assert len(users) <= 0


def test_user_avatars(jira_admin, td):
    # Tests the end-to-end user avatar creation process: upload as temporary,
    # confirm after cropping, and selection.
    size = os.path.getsize(TEST_ICON_PATH)
    # filename = os.path.basename(TEST_ICON_PATH)
    with open(TEST_ICON_PATH, "rb") as icon:
        props = jira_admin.create_temp_user_avatar(
            td['CI_JIRA_ADMIN'], TEST_ICON_PATH, size, icon.read())

    assert 'cropperOffsetX' in props
    assert 'cropperOffsetY' in props
    assert 'cropperWidth' in props
    assert props['needsCropping'] is True

    props['needsCropping'] = False
    avatar_props = jira_admin.confirm_user_avatar(td['CI_JIRA_ADMIN'], props)
    assert 'id' in avatar_props
    assert avatar_props['owner'] == td['CI_JIRA_ADMIN']

    jira_admin.set_user_avatar(td['CI_JIRA_ADMIN'], avatar_props['id'])
    avatars = jira_admin.user_avatars(td['CI_JIRA_ADMIN'])
    assert len(avatars['system']) >= 20  # observed values between 20-24 so far
    assert len(avatars['custom']) >= 1


@pytest.mark.skipif(True, reason="broken: set avatar returns 400")
def test_set_user_avatar(jira_admin, td):
    def find_selected_avatar(avatars):
        for avatar in avatars['system']:
            if avatar['isSelected']:
                return avatar
        # else:
        #     raise Exception as e
        #     print(e)

    avatars = jira_admin.user_avatars(td['CI_JIRA_ADMIN'])

    jira_admin.set_user_avatar(td['CI_JIRA_ADMIN'], avatars['system'][0])
    avatars = jira_admin.user_avatars(td['CI_JIRA_ADMIN'])
    assert find_selected_avatar(avatars)['id'] == avatars['system'][0]

    jira_admin.set_user_avatar(td['CI_JIRA_ADMIN'], avatars['system'][1])
    avatars = jira_admin.user_avatars(td['CI_JIRA_ADMIN'])
    assert find_selected_avatar(avatars)['id'] == avatars['system'][1]


@pytest.mark.skipif(True,
                    reason="disable until I have permissions to write/modify")
# WRONG
def test_delete_user_avatar(jira_admin, td):
    size = os.path.getsize(TEST_ICON_PATH)
    filename = os.path.basename(TEST_ICON_PATH)
    with open(TEST_ICON_PATH, "rb") as icon:
        props = jira_admin.create_temp_user_avatar(
            td['CI_JIRA_ADMIN'], filename, size, icon.read())
    # print(props)
    jira_admin.delete_user_avatar(td['CI_JIRA_ADMIN'], props['id'])


def test_search_users(jira_admin, td):
    users = jira_admin.search_users(td['CI_JIRA_USER'])
    assert len(users) >= 1

    usernames = map(lambda user: user.name, users)
    assert td['CI_JIRA_USER'] in usernames


def test_search_users_maxresults(jira_admin, td):
    users = jira_admin.search_users(td['CI_JIRA_USER'], maxResults=1)
    assert len(users) == 1


def test_search_allowed_users_for_issue_by_project(jira_admin, td):
    users = jira_admin.search_allowed_users_for_issue(
        td['CI_JIRA_USER'], projectKey=td['project_a'])
    assert len(users) >= 1


@not_on_custom_jira_instance
def test_search_allowed_users_for_issue_by_issue(jira_admin, td):
    users = jira_admin.search_allowed_users_for_issue(
        'a', issueKey=td['issue'])
    assert len(users) >= 1


@pytest.mark.xfail(reason='query returns empty list')
def test_search_allowed_users_for_issue_maxresults(jira_admin, td):
    users = jira_admin.search_allowed_users_for_issue(
        'a', projectKey=td['project_b'], maxResults=2)
    assert len(users) <= 2


@pytest.mark.xfail(reason='query returns empty list')
def test_search_allowed_users_for_issue_startat(jira_admin, td):
    users = jira_admin.search_allowed_users_for_issue(
        'c', projectKey=td['project_b'], startAt=1)
    assert len(users) == 0


def test_add_users_to_set(jira_admin, td):
    users_set = set([
        jira_admin.user(td['CI_JIRA_ADMIN']),
        jira_admin.user(td['CI_JIRA_ADMIN'])
    ])
    assert len(users_set) == 1
