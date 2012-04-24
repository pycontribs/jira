import requests
from jira.exceptions import JIRAError
import simplejson as json

class Resource(object):

    def __init__(self, resource, options, cookies=None):
        self.options = options
        self.resource = resource
        self.raw = None
        self.self = None

        if cookies is not None:
            self.cookies = cookies
        else:
            self.cookies = {}

    def find(self, ids=None, headers=None, params=None):
        if ids is None:
            ids = ()

        if isinstance(ids, basestring):
            ids = (ids,)

        if headers is None:
            headers = {}

        if params is None:
            params = {}

        url = self.url(ids)
        headers = self.default_headers(headers)

        r = requests.get(url, headers=headers, params=params, cookies=self.cookies)
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

    def delete(self, **kw):
        """Deletes this resource from the server using a DELETE call. Raises Error
        if deletion isn't implemented.

        """
        pass

    def url(self, ids):
        url = '{}/rest/{}/{}/'.format(self.options['server'], self.options['rest_path'], self.options['rest_api_version'])
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

class Projects(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'project', options, cookies)

class Project(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'project/{0}', options, cookies)
