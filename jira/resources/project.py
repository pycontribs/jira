from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class Projects(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'project', options, cookies)

class Project(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'project/{0}', options, cookies)
