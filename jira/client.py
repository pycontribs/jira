
import pprint as pp
from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class JIRA:

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "rest_path": "/rest/api/2"
    }

    def __init__(self, options=None):
        if options is None:
            options = {}

        self.options = dict(self.__class__.DEFAULT_OPTIONS.items() + options.items())

    def issue(self, id):
        issue = Resource(self.options)
        return issue.find(id, "issue")


def main(argv=None):
     client = JIRA()
     issue_json = client.issue('TST-1')

     pp.pprint(issue_json)

if __name__ == '__main__':
    import sys
    main(sys.argv)