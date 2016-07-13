import pytest


@pytest.fixture
def td(test_manager, jira_admin):
    return {
        'link_types': jira_admin.issue_link_types(),
        'project_b_issue1': test_manager.project_b_issue1,
        'project_b_issue2': test_manager.project_b_issue2
    }


def test_issue_link(jira_admin, td):
    link = jira_admin.issue_link_type(td['link_types'][0].id)

    assert link.id == td['link_types'][0].id


def test_create_issue_link(jira_admin, td):
    jira_admin.create_issue_link(
        td['link_types'][0].outward,
        td['project_b_issue1'],
        td['project_b_issue2'])


def test_create_issue_link_with_issue_objs(jira_admin, td):
    inwardissue = jira_admin.issue(td['project_b_issue1'])

    assert inwardissue is not None

    outwardissue = jira_admin.issue(td['project_b_issue2'])

    assert outwardissue is not None

    jira_admin.create_issue_link(
        td['link_types'][0].outward,
        inwardissue,
        outwardissue)


def test_issue_link_type(jira_admin, td):
    link_type = jira_admin.issue_link_type(td['link_types'][0].id)
    assert link_type.id == td['link_types'][0].id
    assert link_type.name == td['link_types'][0].name
