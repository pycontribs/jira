import re
from jira.exceptions import JIRAError
import simplejson as json

class Resource(object):

    def __init__(self, resource, options, session):
        self._resource = resource
        self._options = options
        self.raw = None
        self.self = None
        self._session = session

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

        r = self._session.get(url, headers=headers, params=params)
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
        dict2resource(raw, self, self._options, self._session)

    def _url(self, ids):
        url = '{server}/rest/{rest_path}/{rest_api_version}/'.format(**self._options)
        url += self._resource.format(*ids)
        return url

    def _default_headers(self, user_headers):
        return dict(user_headers.items() + {'accept': 'application/json'}.items())


def dict2resource(raw, top=None, options=None, session=None):
    if top is None:
        top = type('PropertyHolder', (object,), raw)

    seqs = tuple, list, set, frozenset
    for i, j in raw.iteritems():
        if isinstance(j, dict):
            if 'self' in j:
                resource = cls_for_resource(j['self'])(options, session, j)
                setattr(top, i, resource)
            else:
                setattr(top, i, dict2resource(j, options=options, session=session))
        elif isinstance(j, seqs):
            seq_list = []
            for seq_elem in j:
                if isinstance(seq_elem, dict):
                    if 'self' in seq_elem:
                        resource = cls_for_resource(seq_elem['self'])(options, session, seq_elem)
                        seq_list.append(resource)
                    else:
                        seq_list.append(dict2resource(seq_elem, options=options, session=session))
                else:
                    seq_list.append(seq_elem)
            setattr(top, i, seq_list)
        else:
            setattr(top, i, j)
    return top


class Attachment(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'attachment/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Component(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'component/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class CustomFieldOption(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'customFieldOption/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Dashboards(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'dashboard', options, session)
        if raw:
            self._parse_raw(raw)

class Dashboard(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'dashboard/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Filter(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'filter/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Issue(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Comments(Resource):

    def __init__(self, options, session):
        Resource.__init__(self, 'issue/{0}/comment', options, session)

class Comment(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/comment/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class RemoteLink(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/remotelink/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class Votes(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/votes', options, session)
        if raw:
            self._parse_raw(raw)

class Watchers(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/watchers', options, session)
        if raw:
            self._parse_raw(raw)

class Worklog(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/worklog/{1}', options, session)
        if raw:
            self._parse_raw(raw)

class IssueLink(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issueLink/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class IssueLinkType(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issueLinkType/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class IssueType(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issuetype/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Priority(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'priority/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Project(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'project/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Role(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'project/{0}/role/{1}', options, session)
        if raw:
            self._parse_raw(raw)

class Resolution(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'resolution/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class SecurityLevel(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'securitylevel/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class Status(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'status/{0}', options, session)
        if raw:
            self._parse_raw(raw)

class User(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'user?username={0}', options, session)
        if raw:
            self._parse_raw(raw)

class Version(Resource):

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'version/{0}', options, session)
        if raw:
            self._parse_raw(raw)


resource_class_map = {
    r'attachment/[^/]+$': Attachment,
    r'component/[^/]+$': Component,
    r'customFieldOption/[^/]+$': CustomFieldOption,
    r'dashboard/[^/]+$': Dashboard,
    r'dashboard$': Dashboards,
    r'filter/[^/]$': Filter,
    r'issue/[^/]+$': Issue,
    r'issue/[^/]+/comment$': Comments,
    r'issue/[^/]+/comment/[^/]+$': Comment,
    r'issue/[^/]+/votes$': Votes,
    r'issue/[^/]+/watchers$': Watchers,
    r'issue/[^/]+/worklog/[^/]+$': Worklog,
    r'issueLink/[^/]+$': IssueLink,
    r'issueLinkType/[^/]+$': IssueLinkType,
    r'issuetype/[^/]+$': IssueType,
    r'priority/[^/]+$': Priority,
    r'project/[^/]+$': Project,
    r'project/[^/]+/role/[^/]+$': Role,
    r'resolution/[^/]+$': Resolution,
    r'securitylevel/[^/]+$': SecurityLevel,
    r'status/[^/]+$': Status,
    r'user\?username.+$': User,
    r'version/[^/]+$': Version,
}

def cls_for_resource(resource_literal):
    for resource in resource_class_map:
        if re.search(resource, resource_literal):
            return resource_class_map[resource]
    else:
        # generic Resource without specialized update/delete behavior
        return Resource