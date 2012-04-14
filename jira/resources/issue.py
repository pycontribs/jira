from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class Issue(Resource):

    def __init__(self, options, raw=None):
        Resource.__init__(self, 'issue', options)
        if raw:
            self.raw = raw
            self.self = raw['self']
