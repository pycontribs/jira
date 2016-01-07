import json

import jira.client


def test_template_list():
    text = r'{"projectTemplatesGroupedByType": [ { "projectTemplates": [ { "projectTemplateModuleCompleteKey": "com.pyxis.greenhopper.jira:gh-scrum-template", "name": "Scrum software development"}, { "projectTemplateModuleCompleteKey": "com.pyxis.greenhopper.jira:gh-kanban-template", "name": "Kanban software development"}, { "projectTemplateModuleCompleteKey": "com.pyxis.greenhopper.jira:basic-software-development-template", "name": "Basic software development"} ], "applicationInfo": { "applicationName": "JIRA Software"} }, { "projectTypeBean": { "projectTypeKey": "service_desk", "projectTypeDisplayKey": "Service Desk"}, "projectTemplates": [ { "projectTemplateModuleCompleteKey": "com.atlassian.servicedesk:classic-service-desk-project", "name": "Basic Service Desk"}, { "projectTemplateModuleCompleteKey": "com.atlassian.servicedesk:itil-service-desk-project", "name": "IT Service Desk"} ], "applicationInfo": { "applicationName": "JIRA Service Desk"} }, { "projectTypeBean": { "projectTypeKey": "business", "projectTypeDisplayKey": "Business"}, "projectTemplates": [ { "projectTemplateModuleCompleteKey": "com.atlassian.jira-core-project-templates:jira-core-task-management", "name": "Task management"}, { "projectTemplateModuleCompleteKey": "com.atlassian.jira-core-project-templates:jira-core-project-management", "name": "Project management"}, { "projectTemplateModuleCompleteKey": "com.atlassian.jira-core-project-templates:jira-core-process-management", "name": "Process management"} ], "applicationInfo": { "applicationName": "JIRA Core"} }], "maxNameLength": 80, "minNameLength": 2, "maxKeyLength": 10 }'
    j = json.loads(text)
    template_list = jira.client._get_template_list(j)
    assert [t['name'] for t in template_list] == ["Scrum software development", "Kanban software development", "Basic software development",
                                                  "Basic Service Desk", "IT Service Desk", "Task management", "Project management",
                                                  "Process management"]
