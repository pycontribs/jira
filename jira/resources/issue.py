from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class Issue(Resource):

    def __init__(self, options, raw=None):
        Resource.__init__(self, 'issue/{0}', options)
        if raw:
            self.raw = raw
            self.self = raw['self']

class CreateMeta(Resource):

    def __init__(self, options):
        Resource.__init__(self, 'issue/createmeta', options)

class Comments(Resource):

    def __init__(self, options):
        Resource.__init__(self, 'issue/{0}/comment', options)

class Comment(Resource):

    def __init__(self, options, raw=None):
        Resource.__init__(self, 'issue/{0}/comment/{1}', options)
        if raw:
            self.raw = raw
            self.self = raw['self']
