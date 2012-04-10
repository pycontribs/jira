from jira.resources.resource import Resource

__author__ = 'bspeakmon@atlassian.com'

class Project(Resource):

    def __init__(self, options):
        Resource.__init__(self, options)
