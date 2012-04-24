from jira.client import JIRA
import pprint as pp

jira = JIRA(basic_auth=('admin', 'admin'))

props = jira.application_properties()
#jira.set_application_property('jira.clone.prefix', 'horseflesh')

meta = jira.attachment_meta()

# auto issue lookup
issue = jira.issue('TST-3')
print 'Issue {} reported by {} has {} comments.'.format(
    issue.key, issue.fields.assignee.name, issue.fields.comment.total
)

# auto project lookup
project = jira.project('TST')
print 'Project {} has key {} and {} components.'.format(
    project.name, project.key, len(project.components)
)

# generic resource lookup; create a Resource subclass for this
#resource = jira.find('TST-1', 'issue')
#pp.pprint(resource.self)

# even more generic resource lookup
generic_options = {
    'server': 'http://localhost:2990/jira',
    'rest_path': 'api',
    'rest_api_version': '2'
}
#resource = jira.find('TST', 'project', generic_options)
#pp.pprint(resource.self)

# jql search
issues = jira.search_issues('project=TST')
for issue in issues:
    pp.pprint(issue.self)

# comments
comments = jira.comments('TST-1')
for comment in comments:
    pp.pprint(comment.self)

comment = jira.comment('TST-1', '10001')
pp.pprint(comment.raw)
print 'Comment ID: {}'.format(comment.id)
print '  Author: {}'.format(comment.author.name)
print '  Text: {}'.format(comment.body)
