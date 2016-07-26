import re
import sys
import json
import pytest
import getpass
from jira import JIRAError, JIRA

import jira.client


@pytest.fixture(scope='function')
def slug(request, jira_admin):
    def remove_by_slug():
        try:
            jira_admin.delete_project(slug)
        except ValueError:
            # Some tests have project already removed, so we stay silent
            pass

    prefix = (
        'T' + (re.sub("[^A-Z]", "", getpass.getuser().upper()))[0:6] +
        str(sys.version_info[0]) + str(sys.version_info[1])
    )

    slug = prefix + 'T'
    project_name = (
        "Test user=%s key=%s A" % (getpass.getuser(), slug)
    )

    already_exists = True
    try:
        proj = jira_admin.project(slug)
    except JIRAError:
        already_exists = False

    if not already_exists:
        proj = jira_admin.create_project(slug, project_name)
        assert proj

    request.addfinalizer(remove_by_slug)

    return slug


def test_delete_project(jira_admin, slug):
    assert jira_admin.delete_project(slug)


def test_delete_inexistant_project(jira_admin):
    slug = 'abogus123'
    with pytest.raises(ValueError) as ex:
        assert jira_admin.delete_project(slug)

    assert (
        'Parameter pid="%s" is not a Project, projectID or slug' % slug in
        str(ex.value)
    )


def test_no_rights_to_delete_project(jira_normal, slug):
    with pytest.raises(JIRAError) as ex:
        assert jira_normal.delete_project(slug)

    assert 'Not enough permissions to delete project' in str(ex.value)


def test_session_invalid_login():
    with pytest.raises(JIRAError) as je:
        JIRA('https://support.atlassian.com',
             basic_auth=("xxx", "xxx"),
             validate=True,
             logging=False)

    e = je.value
    assert e.status_code == 401


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
