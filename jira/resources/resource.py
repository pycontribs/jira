__author__ = 'bspeakmon@atlassian.com'

import requests
import simplejson as json

class Resource(object):

    def __init__(self, options):
        self.options = options
        self.raw = None
        self.self = None

    def find(self, id, resource=None, headers=None):
        if resource is None:
            resource = self.__class__.__name__.lower()

        if headers is None:
            headers = {}

        r = requests.get(self._url(resource, id), headers=self._default_headers(headers))
        self.raw = json.loads(r.text)
        self.self = self.raw['self']

    def _url(self, resource, id):
        return self.options['server'] + self.options['rest_path'] + '/' + resource + '/' + id

    def _default_headers(self, user_headers):
        return dict(user_headers.items() + {'accept': 'application/json'}.items())
