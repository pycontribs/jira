
import pprint as pp
from jira.resources.issue import Issue
from jira.resources.resource import Resource

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


def main(argv=None):
     client = JIRA()

     # auto issue lookup
     issue = client.issue('TST-1')
     pp.pprint(issue.self)

     # manual issue lookup
     issue = client.issue()
     issue.find(id='TST-1')
     pp.pprint(issue.self)

if __name__ == '__main__':
    import sys
    main(sys.argv)