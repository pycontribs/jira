"""
This module implements the Resource classes that translate JSON from JIRA REST resources
into usable objects.
"""

import re
from jira.exceptions import JIRAError
import json

class Resource(object):
    """
    Models a URL-addressable resource in the JIRA REST API.

    All Resource objects provide the following:
    find() -- get a resource from the server and load it into the current object
        (though clients should use the methods in the JIRA class instead of this method directly)
    update() -- changes the value of this resource on the server and returns a new resource object for it
    delete() -- deletes this resource from the server
    self -- the URL of this resource on the server
    raw -- dict of properties parsed out of the JSON response from the server

    Subclasses will implement update() and delete() as appropriate for the specific resource.

    All Resources have a resource path of the form:

    * 'issue'
    * 'project/{0}'
    * 'issue/{0}/votes'
    * 'issue/{0}/comment/{1}

    where the bracketed numerals are placeholders for ID values that are filled in from the
    'ids' parameter to find().
    """

    def __init__(self, resource, options, session):
        self._resource = resource
        self._options = options
        self._session = session

        # explicitly define as None so we know when a resource has actually been loaded
        self.raw = None
        self.self = None

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
            msg = "Couldn't find resource: '" + self.__class__.__name__ + "' with ids " + ids.__str__()
            raise JIRAError(msg, r.status_code, url)

        self._parse_raw(json.loads(r.text))

    def update(self, **kwargs):
        """
        Updates this resource on the server, marshaling the given keyword parameters
        into the necessary format for this resource.
        """
        pass

    def delete(self, **kw):
        """
        Deletes this resource from the server.
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
    """
    Recursively walks a dict structure, transforming the properties into attributes
    on a new Resource object of the appropriate type (if a 'self' link is present)
    or a PropertyHolder object (if no 'self' link is present).
    """
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
    """An issue attachment."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'attachment/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Component(Resource):
    """A project component."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'component/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class CustomFieldOption(Resource):
    """An existing option for a custom issue field."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'customFieldOption/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Dashboards(Resource):
    """A collection of dashboards."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'dashboard', options, session)
        if raw:
            self._parse_raw(raw)


class Dashboard(Resource):
    """A JIRA dashboard."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'dashboard/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Filter(Resource):
    """An issue navigator filter."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'filter/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Issue(Resource):
    """A JIRA issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Comments(Resource):
    """A collection of issue comments."""

    def __init__(self, options, session):
        Resource.__init__(self, 'issue/{0}/comment', options, session)


class Comment(Resource):
    """An issue comment."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/comment/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class RemoteLink(Resource):
    """A link to a remote application from an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/remotelink/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class Votes(Resource):
    """Vote information on an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/votes', options, session)
        if raw:
            self._parse_raw(raw)


class Watchers(Resource):
    """Watcher information on an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/watchers', options, session)
        if raw:
            self._parse_raw(raw)


class Worklog(Resource):
    """Worklog on an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/worklog/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class IssueLink(Resource):
    """Link between two issues."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issueLink/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class IssueLinkType(Resource):
    """Type of link between two issues."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issueLinkType/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class IssueType(Resource):
    """Type of an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issuetype/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Priority(Resource):
    """Priority that can be set on an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'priority/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Project(Resource):
    """A JIRA project."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'project/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Role(Resource):
    """A role inside a project."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'project/{0}/role/{1}', options, session)
        if raw:
            self._parse_raw(raw)


class Resolution(Resource):
    """A resolution for an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'resolution/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class SecurityLevel(Resource):
    """A security level for an issue or project."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'securitylevel/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Status(Resource):
    """Status for an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'status/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class User(Resource):
    """A JIRA user."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'user?username={0}', options, session)
        if raw:
            self._parse_raw(raw)


class Version(Resource):
    """A version of a project."""

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