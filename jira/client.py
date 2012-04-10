
import pprint as pp
from jira.resources.issue import Issue
from jira.resources.project import Project

__author__ = 'bspeakmon@atlassian.com'

class JIRA(object):

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "rest_path": "/rest/api/2"
    }

    def __init__(self, options=None):
        if options is None:
            options = {}

        self.options = dict(self.__class__.DEFAULT_OPTIONS.items() + options.items())

    def issue(self, id=None):
        issue = Issue(self.options)

        if not id is None:
            issue.find(id)

        return issue

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

if __name__ == '__main__':
    import sys
    main(sys.argv)