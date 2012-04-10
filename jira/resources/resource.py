__author__ = 'bspeakmon@atlassian.com'

import requests
import simplejson as json

class JIRAError(Exception):
    def __init__(self, url, status_code, msg):
        self.url = url
        self.status_code = status_code
        self.msg = msg

class Resource(object):

    def __init__(self, resource, options):
        self.options = options
        self.resource = resource
        self.raw = None
        self.self = None

    def find(self, id, headers=None):
        if headers is None:
            headers = {}

        r = requests.get(self._url(id), headers=self._default_headers(headers))
        if r.status_code >= 400:
            raise JIRAError(self._url, r.status_code, 'GET failed')

        self.raw = json.loads(r.text)
        self.self = self.raw['self']

    def save(self):
        """Saves this resource to the server, using POST/PUT/whatever combination
        is required for this resource (subclasses will handle details). Raises Error
        if saving isn't implemented.

        """
        pass

    def delete(self):
        """Deletes this resource from the server using a DELETE call. Raises Error
        if deletion isn't implemented.

        """
        pass

    def _url(self, id):
        return self.options['server'] + self.options['rest_path'] + '/' + self.options['rest_api_version'] + '/' + self.resource + '/' + id

    def _default_headers(self, user_headers):
        return dict(user_headers.items() + {'accept': 'application/json'}.items())
