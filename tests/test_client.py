from flaky import flaky
import getpass
import json
import pytest
from tests import get_unique_project_name
from tests import JiraTestManager
import time

from jira import Role, Issue, JIRA, JIRAError, Project  # noqa
import jira.client


@pytest.fixture(scope='module')
def test_manager():
    return JiraTestManager()


@pytest.fixture()
def cl_admin(test_manager):
    return test_manager.jira_admin


@pytest.fixture()
def cl_normal(test_manager):
    return test_manager.jira_normal


@pytest.fixture(scope='function')
def slug(request, cl_admin):
    def remove_by_slug():
        try:
            cl_admin.delete_project(slug)
        except ValueError:
            # Some tests have project already removed, so we stay silent
            pass

    slug = get_unique_project_name()

    project_name = (
        "Test user=%s key=%s A" % (getpass.getuser(), slug)
    )

    try:
        proj = cl_admin.project(slug)
    except JIRAError:
        proj = cl_admin.create_project(slug, project_name)
    assert proj

    request.addfinalizer(remove_by_slug)

    return slug


@flaky
@pytest.mark.xfail(reason='fails often but only with Travis')
def test_delete_project(cl_admin, cl_normal, slug):
    time.sleep(6)  # with <=5s was failing often

    with pytest.raises(JIRAError) as ex:
        assert cl_normal.delete_project(slug)

    assert 'Not enough permissions to delete project' in str(ex.value)

    try:
        assert cl_admin.delete_project(slug)
    except Exception as e:
        e.message += " slug=%s" % slug
        raise


def test_delete_inexistant_project(cl_admin):
    slug = 'abogus123'
    with pytest.raises(ValueError) as ex:
        assert cl_admin.delete_project(slug)

    assert (
        'Parameter pid="%s" is not a Project, projectID or slug' % slug in
        str(ex.value)
    )


def test_template_list():
    text = (
    r'{"projectTemplatesGroupedByType": ['
    ' { "projectTemplates": [ { "projectTemplateModuleCompleteKey": '
        '"com.pyxis.greenhopper.jira:gh-scrum-template", '
        '"name": "Scrum software development"}, '
        '{ "projectTemplateModuleCompleteKey": '
        '"com.pyxis.greenhopper.jira:gh-kanban-template", '
        '"name": "Kanban software development"}, '
        '{ "projectTemplateModuleCompleteKey": '
        '"com.pyxis.greenhopper.jira:'
        'basic-software-development-template",'
        ' "name": "Basic software development"} ],'
        ' "applicationInfo": { '
        '"applicationName": "JIRA Software"} }, '
        '{ "projectTypeBean": { '
        '"projectTypeKey": "service_desk", '
        '"projectTypeDisplayKey": "Service Desk"}, '
        '"projectTemplates": [ { '
        '"projectTemplateModuleCompleteKey": '
        '"com.atlassian.servicedesk:classic-service-desk-project", '
        '"name": "Basic Service Desk"},'
        ' { "projectTemplateModuleCompleteKey": '
        '"com.atlassian.servicedesk:itil-service-desk-project",'
        ' "name": "IT Service Desk"} ], '
        '"applicationInfo": { '
        '"applicationName": "JIRA Service Desk"} }, '
        '{ "projectTypeBean": { '
        '"projectTypeKey": "business", '
        '"projectTypeDisplayKey": "Business"}, '
        '"projectTemplates": [ { '
        '"projectTemplateModuleCompleteKey": '
        '"com.atlassian.jira-core-project-templates:jira-core-task-management", '
        '"name": "Task management"}, {'
        ' "projectTemplateModuleCompleteKey": '
        '"com.atlassian.jira-core-project-templates:jira-core-project-management", '
        '"name": "Project management"}, { '
        '"projectTemplateModuleCompleteKey": '
        '"com.atlassian.jira-core-project-templates:jira-core-process-management", '
        '"name": "Process management"} ], '
        '"applicationInfo": { "applicationName": "JIRA Core"} }],'
        ' "maxNameLength": 80, "minNameLength": 2, "maxKeyLength": 10 }'
    )  # noqa
    j = json.loads(text)
    template_list = jira.client._get_template_list(j)
    assert [t['name'] for t in template_list] == ["Scrum software development", "Kanban software development", "Basic software development",
                                                  "Basic Service Desk", "IT Service Desk", "Task management", "Project management",
                                                  "Process management"]
