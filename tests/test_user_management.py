import pytest
from tests import JiraTestManager
from tests import rndpassword

from jira import JIRAError


@pytest.fixture(scope='module')
def test_manager():
    return JiraTestManager()


@pytest.fixture(scope='module')
def td(test_manager):
    return {
        'test_username': 'test_%s' % test_manager.project_a,
        'test_email': 'test_%s@example.com' % test_manager.project_a,
        'test_password': rndpassword(),
        'test_groupname': 'testGroupFor_%s' % test_manager.project_a
    }


@pytest.fixture()
def jira_admin(test_manager):
    return test_manager.jira_admin


def test_add_and_remove_user(td, jira_admin):

    try:
        jira_admin.delete_user(td['test_username'])
    except JIRAError:
        # we ignore if it fails to delete from start because we don't
        # know if it already existed
        pass

    result = jira_admin.add_user(
        td['test_username'],
        td['test_email'],
        password=td['test_password'])

    assert result is True

    try:
        # Make sure user exists before attempting test to delete.
        jira_admin.add_user(
            td['test_username'],
            td['test_email'],
            password=td['test_password'])
    except JIRAError:
        pass

    result = jira_admin.delete_user(td['test_username'])
    assert result is True

    x = jira_admin.search_users(td['test_username'])
    assert len(x) == 0, (
        "Found test user when it should have been deleted. Test Fails.")


def test_add_group(td, jira_admin):
    try:
        jira_admin.remove_group(td['test_groupname'])
    except JIRAError:
        pass

    result = jira_admin.add_group(td['test_groupname'])
    assert result is True

    x = jira_admin.groups(query=td['test_groupname'])
    assert td['test_groupname'] == x[0], (
        "Did not find expected group after trying to add it. Test Fails.")
    jira_admin.remove_group(td['test_groupname'])


def test_remove_group(td, jira_admin):
    try:
        jira_admin.add_group(td['test_groupname'])
    except JIRAError:
        pass

    result = jira_admin.remove_group(td['test_groupname'])
    assert result is True

    x = jira_admin.groups(query=td['test_groupname'])
    assert len(x) == 0, (
        'Found group with name when it should have been deleted. Test Fails.')


def test_add_user_to_group(td, jira_admin):
    try:
        jira_admin.add_user(
            td['test_username'],
            td['test_email'],
            password=td['test_password'])
        jira_admin.add_group(td['test_groupname'])
        # Just in case user is already there.
        jira_admin.remove_user_from_group(
            td['test_username'], td['test_groupname'])
    except JIRAError:
        pass

    result = jira_admin.add_user_to_group(
        td['test_username'], td['test_groupname'])
    assert result is True

    x = jira_admin.group_members(td['test_groupname'])
    assert td['test_username'] in x.keys(), (
        'Username not returned in group member list. Test Fails.')
    assert 'email' in x[td['test_username']]
    assert 'fullname' in x[td['test_username']]
    assert 'active' in x[td['test_username']]
    jira_admin.remove_group(td['test_groupname'])
    jira_admin.delete_user(td['test_username'])


def test_remove_user_from_group(td, jira_admin):
    try:
        jira_admin.add_user(
            td['test_username'],
            td['test_email'],
            password=td['test_password'])
        jira_admin.add_group(td['test_groupname'])
        jira_admin.add_user_to_group(
            td['test_username'], td['test_groupname'])
    except JIRAError:
        pass

    result = jira_admin.remove_user_from_group(
        td['test_username'], td['test_groupname'])
    assert result is True

    x = jira_admin.group_members(td['test_groupname'])
    assert td['test_username'] not in x.keys(), (
        'Username found in group when it should have been removed. '
        'Test Fails.')

    jira_admin.remove_group(td['test_groupname'])
    jira_admin.delete_user(td['test_username'])
