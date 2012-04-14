
import pprint as pp
from jira.resources.issue import Issue
from jira.resources.project import Project
from jira.resources.resource import Resource
from jira.resources.search import Search

__author__ = 'bspeakmon@atlassian.com'

class JIRA(object):

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira/rest",
        "rest_path": "/api",
        "rest_api_version": "2"
    }

    def __init__(self, options=None):
        if options is None:
            options = {}

        self.options = dict(JIRA.DEFAULT_OPTIONS.items() + options.items())

    def find(self, id, resource_name, options=None):
        if options is None:
            options = {}

        resource_options = dict(self.options.items() + options.items())
        resource = Resource(resource_name, resource_options)
        resource.find(id)
        return resource

    def get_issue(self, id):
        issue = Issue(self.options)
        issue.find(id)
        return issue

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

        issues = [Issue(self.options, issue) for issue in resource.raw['issues']]
        return issues

    def get_project(self, id):
        project = Project(self.options)
        project.find(id)
        return project


def main(argv=None):
    jira = JIRA()

    # auto issue lookup
    issue = jira.get_issue('TST-1')
    #pp.pprint(issue.raw)

    # auto project lookup
    project = jira.get_project('TST')
    pp.pprint(project.self)

    # generic resource lookup
    resource = jira.find('TST-1', 'issue')
    pp.pprint(resource.self)

    # even more generic resource lookup
    generic_options = {
        'server': 'http://localhost:2990/jira/rest',
        'rest_path': '/api',
        'rest_api_version': '2'
    }
    resource = jira.find('TST', 'project', generic_options)
    pp.pprint(resource.self)

    # jql search
    issues = jira.search_issues('project=TST')
    for issue in issues:
        pp.pprint(issue.self)

if __name__ == '__main__':
    import sys
    main(sys.argv)