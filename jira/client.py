
import pprint as pp
from jira.resources import resource
from jira.resources.issue import Issue, Comments, Comment
from jira.resources.project import Project
from jira.resources.resource import Resource
from jira.resources.search import Search

__author__ = 'bspeakmon@atlassian.com'

class JIRA(object):

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "rest_path": "api",
        "rest_api_version": "2"
    }

    def __init__(self, options=None):
        if options is None:
            options = {}

        self.options = dict(JIRA.DEFAULT_OPTIONS.items() + options.items())

### Universal resource loading

    def find(self, id, resource_name, options=None):
        if options is None:
            options = {}

        resource_options = dict(self.options.items() + options.items())
        resource = Resource(resource_name, resource_options)
        resource.find(id)
        return resource

### Application properties

### Attachments

### Components

### Custom field options

### Dashboards

### Fields

### Filters

### Groups

### Issues

    def get_issue(self, id):
        issue = Issue(self.options)
        issue.find(id)
        return issue

    def get_comments(self, issue):
        resource = Comments(self.options)
        resource.find(issue)

        comments = [Comment(self.options, raw_comment_json) for raw_comment_json in resource.raw['comments']]
        return comments

    def get_comment(self, issue, comment):
        resource = Comment(self.options)
        resource.find((issue, comment))
        return resource


### Issue links

### Issue link types

### Issue types

### User permissions

### Priorities

### Projects

    def get_project(self, id):
        project = Project(self.options)
        project.find(id)
        return project

### Resolutions

### Search

    def search_issues(self, jql_str, start=0, max=50, fields=None, expand=None):
        if fields is None:
            fields = []

        search_params = {
            "jql": jql_str,
            "startAt": start,
            "maxResults": max,
            "fields": fields,
            "expand": expand
        }

        resource = Search(self.options)
        resource.find(params=search_params)

        issues = [Issue(self.options, raw_issue_json) for raw_issue_json in resource.raw['issues']]
        return issues

### Security levels

### Server info

### Status

### Users

### Versions

### Session authentication

### Websudo



def main(argv=None):
    jira = JIRA()

    # auto issue lookup
    issue = jira.get_issue('TST-1')
    pp.pprint(issue.raw)

    # auto project lookup
    project = jira.get_project('TST')
    pp.pprint(project.self)

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
    comments = jira.get_comments('TST-1')
    for comment in comments:
        pp.pprint(comment.self)

    comment = jira.get_comment('TST-1', '10002')
    pp.pprint(comment.raw)

if __name__ == '__main__':
    import sys
    main(sys.argv)