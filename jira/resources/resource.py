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

    def find(self, ids=None, headers=None, params=None):
        if ids is None:
            ids = ()

        if not isinstance(ids, tuple):
            ids = (ids,)

        if headers is None:
            headers = {}

        if params is None:
            params = {}

        url = self.url(ids)
        headers = self.default_headers(headers)

        r = requests.get(url, headers=headers, params=params)
        if r.status_code >= 400:
            raise JIRAError(url, r.status_code, 'GET failed')

        self.raw = json.loads(r.text)
        json_obj = dict2obj(self.raw)
        self.__dict__.update(json_obj.__dict__)
        self.self = self.raw.get('self')

    def update(self, **kwargs):
        """Updates this resource on the server, marshaling the given keyword parameters
        into a JSON object sent via PUT/POST (depending on the implementation). Raises Error
        if saving isn't implemented.

        """
        pass

    def delete(self):
        """Deletes this resource from the server using a DELETE call. Raises Error
        if deletion isn't implemented.

        """
        pass

    def url(self, ids):
        url = '%s/rest/%s/%s/' % (self.options['server'], self.options['rest_path'], self.options['rest_api_version'])
        url += self.resource.format(*ids)
        return url

    def default_headers(self, user_headers):
        return dict(user_headers.items() + {'accept': 'application/json'}.items())

def dict2obj(d):
    top = type('new', (object,), d)
    seqs = tuple, list, set, frozenset
    for i, j in d.iteritems():
        if isinstance(j, dict):
            setattr(top, i, dict2obj(j))
        elif isinstance(j, seqs):
            setattr(top, i,
                type(j) (dict2obj(sj) if isinstance(sj, dict) else sj for sj in j))
        else:
            setattr(top, i, j)
    return top