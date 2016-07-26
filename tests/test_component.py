import pytest
from tests import rndstr
from jira import JIRAError


def test_create_component(test_manager, jira_admin):
    proj = jira_admin.project(test_manager.project_b)
    name = "project-%s-component-%s" % (proj, rndstr())
    component = jira_admin.create_component(
        name,
        proj,
        description='test!!',
        assigneeType='COMPONENT_LEAD',
        isAssigneeTypeValid=False)
    assert component.name == name
    assert component.description == 'test!!'
    assert component.assigneeType == 'COMPONENT_LEAD'
    assert component.isAssigneeTypeValid is False
    component.delete()


def test_update_component(test_manager, jira_admin):
    try:
        components = jira_admin.project_components(test_manager.project_b)
        for component in components:
            if component.name == 'To be updated':
                component.delete()
                break
    except Exception:
        # We ignore errors as this code intends only to prepare for
        # component creation
        pass

    name = 'component-' + rndstr()

    component = jira_admin.create_component(
        name,
        test_manager.project_b,
        description='stand by!',
        leadUserName=test_manager.CI_JIRA_ADMIN)
    name = 'renamed-' + name
    component.update(name=name,
                     description='It is done.',
                     leadUserName=test_manager.CI_JIRA_ADMIN)
    assert component.name == name
    assert component.description == 'It is done.'
    assert component.lead.name == test_manager.CI_JIRA_ADMIN
    component.delete()


def test_delete_component(test_manager, jira_admin):
    component = jira_admin.create_component(
        'To be deleted',
        test_manager.project_b,
        description='not long for this world')
    myid = component.id
    component.delete()
    with pytest.raises(JIRAError):
        jira_admin.component(myid)

# COmponents field can't be modified from issue.update
#    def test_component_count_related_issues(test_manager, jira_admin):
#        component = jira_admin.create_component('PROJECT_B_TEST',self.project_b, description='test!!',
#                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
#        issue1 = jira_admin.issue(self.issue_1)
#        issue2 = jira_admin.issue(self.issue_2)
#        (issue1.update ({'components': ['PROJECT_B_TEST']}))
#        (issue2.update (components = ['PROJECT_B_TEST']))
#        issue_count = jira_admin.component_count_related_issues(component.id)
#        self.assertEqual(issue_count, 2)
#        component.delete()
