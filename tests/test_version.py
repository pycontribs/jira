import pytest
from jira import JIRAError


@pytest.fixture
def td(test_manager):
    return {
        'project_b': test_manager.project_b,
        'project_b_issue1': test_manager.project_b_issue1
    }


def test_create_version(jira_admin, td):
    version = jira_admin.create_version(
        'new version 1',
        td['project_b'],
        releaseDate='2015-03-11',
        description='test version!')

    assert version.name == 'new version 1'
    assert version.description == 'test version!'
    assert version.releaseDate == '2015-03-11'

    version.delete()


def test_create_version_with_project_obj(jira_admin, td):
    project = jira_admin.project(td['project_b'])
    version = jira_admin.create_version(
        'new version 1',
        project,
        releaseDate='2015-03-11',
        description='test version!')

    assert version.name == 'new version 1'
    assert version.description == 'test version!'
    assert version.releaseDate == '2015-03-11'

    version.delete()


def test_update(jira_admin, td):
    version = jira_admin.create_version(
        'new updated version 1',
        td['project_b'],
        releaseDate='2015-03-11',
        description='new to be updated!')
    version.update(
        name='new updated version name 1',
        description='new updated!')

    assert version.name == 'new updated version name 1'
    assert version.description == 'new updated!'

    v = jira_admin.version(version.id)
    assert v == version
    assert v.id == version.id

    version.delete()


def test_delete(jira_admin, td):
    version = jira_admin.create_version(
        'To be deleted',
        td['project_b'],
        releaseDate='2015-03-11',
        description='not long for this world')

    myid = version.id
    version.delete()

    with pytest.raises(JIRAError):
        jira_admin.version(myid)


def test_version_expandos(jira_admin):
    pass
