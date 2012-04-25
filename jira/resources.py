import requests
from jira.exceptions import JIRAError
import simplejson as json
from jira.utils import dict2obj

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

        url = self._url(ids)
        headers = self._default_headers(headers)

        r = requests.get(url, headers=headers, params=params, cookies=self.cookies)
        if r.status_code >= 400:
            raise JIRAError(url, r.status_code, 'GET failed')

        self._parse_raw(json.loads(r.text))

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

    def _parse_raw(self, raw):
        self.raw = raw
        json_obj = dict2obj(raw)
        self.__dict__.update(json_obj.__dict__)

    def _url(self, ids):
        url = '{}/rest/{}/{}/'.format(self.options['server'], self.options['rest_path'], self.options['rest_api_version'])
        url += self.resource.format(*ids)
        return url

    def _default_headers(self, user_headers):
        return dict(user_headers.items() + {'accept': 'application/json'}.items())



class Attachment(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'attachment/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Component(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'component/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Dashboards(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'dashboard', options, cookies)
        if raw:
            self._parse_raw(raw)

class Dashboard(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'dashboard/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Filter(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'filter/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)


class Issue(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issue/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Comments(Resource):

    def __init__(self, options, cookies=None):
        Resource.__init__(self, 'issue/{0}/comment', options, cookies)

class Comment(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issue/{0}/comment/{1}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Votes(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issue/{0}/votes', options, cookies)
        if raw:
            self._parse_raw(raw)

class Watchers(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issue/{0}/watchers', options, cookies)
        if raw:
            self._parse_raw(raw)

class Worklog(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issue/{0}/worklog', options, cookies)
        if raw:
            self._parse_raw(raw)

class IssueLink(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issueLink/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class IssueLinkType(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issueLinkType/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class IssueType(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'issuetype/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Priority(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'priority/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Project(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'project/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Role(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'project/{0}/role/{1}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Resolution(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'resolution/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class SecurityLevel(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'securitylevel/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Status(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'status/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class User(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'user?username={0}', options, cookies)
        if raw:
            self._parse_raw(raw)

class Version(Resource):

    def __init__(self, options, cookies=None, raw=None):
        Resource.__init__(self, 'version/{0}', options, cookies)
        if raw:
            self._parse_raw(raw)
