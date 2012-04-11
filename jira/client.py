
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

    def find(self, id, resource_name, **kwargs):
        resource_options = dict(self.options.items() + kwargs.items())
        resource = Resource(resource_name, resource_options)
        resource.find(id)
        return resource

    def issue(self, id=None):
        issue = Issue(self.options)

        if not id is None:
            issue.find(id)

        return issue

    def issues(self, jql_str):
        return self.search(jql_str)

    def search(self, jql_str, start=0, max=50, fields=None, expand=None):
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
        return resource

    def project(self, id=None):
        project = Project(self.options)

        if not id is None:
            project.find(id)

        return project


def main(argv=None):
     client = JIRA()

     # auto issue lookup
     issue = client.issue('TST-1')
     pp.pprint(issue.self)

     # manual issue lookup
     issue = client.issue()
     issue.find('TST-1')
     pp.pprint(issue.self)

     project = client.project('TST')
     pp.pprint(project.self)

     project = client.project()
     project.find('TST')
     pp.pprint(project.self)

     # generic resource lookup
     resource = client.find('TST-1', 'issue')
     pp.pprint(resource.self)

     # even more generic resource lookup
     resource = client.find('TST', 'project', server='http://localhost:2990/jira/rest', rest_path='/api', rest_api_version='2')
     pp.pprint(resource.self)

     # jql search
     resource = client.search('project=TST')
     pp.pprint(resource.raw)

if __name__ == '__main__':
    import sys
    main(sys.argv)