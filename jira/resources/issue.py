from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class Issue(Resource):

    def __init__(self, options, raw=None, cookies=None):
        Resource.__init__(self, 'issue/{0}', options, cookies)
        if raw:
            self.raw = raw
            self.self = raw['self']

class CreateMeta(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'issue/createmeta', options, cookies)

class Comments(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'issue/{0}/comment', options, cookies)

class Comment(Resource):

    def __init__(self, options, raw=None, cookies=None):
        Resource.__init__(self, 'issue/{0}/comment/{1}', options, cookies)
        if raw:
            self.raw = raw
            self.self = raw['self']
