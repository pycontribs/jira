# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
"""
This module implements the Resource classes that translate JSON from JIRA REST resources
into usable objects.
"""

import re
import sys
import logging
import random
import pprint
import json

from six import iteritems, string_types, text_type
from six import print_ as print

from jira.exceptions import raise_on_error, get_error_list


class Resource(object):

    """
    Models a URL-addressable resource in the JIRA REST API.

    All Resource objects provide the following:
    ``find()`` -- get a resource from the server and load it into the current object
    (though clients should use the methods in the JIRA class instead of this method directly)
    ``update()`` -- changes the value of this resource on the server and returns a new resource object for it
    ``delete()`` -- deletes this resource from the server
    ``self`` -- the URL of this resource on the server
    ``raw`` -- dict of properties parsed out of the JSON response from the server

    Subclasses will implement ``update()`` and ``delete()`` as appropriate for the specific resource.

    All Resources have a resource path of the form:

    * ``issue``
    * ``project/{0}``
    * ``issue/{0}/votes``
    * ``issue/{0}/comment/{1}``

    where the bracketed numerals are placeholders for ID values that are filled in from the
    ``ids`` parameter to ``find()``.
    """

    # A prioritized list of the keys in self.raw most likely to contain a human
    # readable name or identifier, or that offer other key information.
    _READABLE_IDS = ('displayName', 'key', 'name', 'filename', 'value',
                     'scope', 'votes', 'id', 'mimeType', 'closed')

    def __init__(self, resource, options, session):
        self._resource = resource
        self._options = options
        self._session = session

        # Explicitly define as None so we know when a resource has actually been loaded
        self.raw = None
        self.self = None

    def __str__(self):
        # Return the first value we find that is likely to be human readable.
        if self.raw:
            for name in self._READABLE_IDS:
                if name in self.raw:
                    pretty_name = text_type(self.raw[name])
                    # Include any child to support nested select fields.
                    if hasattr(self, 'child'):
                        pretty_name += ' - ' + text_type(self.child)
                    return pretty_name

        # If all else fails, use repr to make sure we get something.
        return repr(self)

    def __repr__(self):
        # Identify the class and include any and all relevant values.
        names = []
        if self.raw:
            for name in self._READABLE_IDS:
                if name in self.raw:
                    names.append(name + '=' + repr(self.raw[name]))
        if not names:
            return '<JIRA %s at %s>' % (self.__class__.__name__,
                                        text_type(hex(id(self))))
        return '<JIRA %s: %s>' % (self.__class__.__name__, ', '.join(names))

    def find(self, ids=None, headers=None, params=None):
        if ids is None:
            ids = ()

        if isinstance(ids, string_types):
            ids = (ids,)

        if headers is None:
            headers = {}

        if params is None:
            params = {}

        url = self._url(ids)
        headers = self._default_headers(headers)
        self._load(url, headers, params)

    def update(self, async=None, jira=None, **kwargs):
        """
        Update this resource on the server. Keyword arguments are marshalled into a dict before being sent. If this
        resource doesn't support ``PUT``, a :py:exc:`.JIRAError` will be raised; subclasses that specialize this method
        will only raise errors in case of user error.

        :param async: if true the request will be added to the queue so it can be executed later using async_run()
        """
        if async is None:
            async = self._options['async']

        data = {}
        for arg in kwargs:
            data[arg] = kwargs[arg]

        r = self._session.put(self.self, headers={'content-type': 'application/json'}, data=json.dumps(data))
        if 'autofix' in self._options and \
                r.status_code == 400:
            user = None
            error_list = get_error_list(r)
            logging.error(error_list)
            if "The reporter specified is not a user." in error_list:
                if 'reporter' not in data['fields']:
                    logging.warning("autofix: setting reporter to '%s' and retrying the update." % self._options['autofix'])
                    data['fields']['reporter'] = {'name': self._options['autofix']}

            if "Issues must be assigned." in error_list:
                if 'assignee' not in data['fields']:
                    logging.warning("autofix: setting assignee to '%s' for %s and retrying the update." % (self._options['autofix'], self.key))
                    data['fields']['assignee'] = {'name': self._options['autofix']}
                    # for some reason the above approach fails on Jira 5.2.11 so we need to change the assignee before

            if "Issue type is a sub-task but parent issue key or id not specified." in error_list:
                logging.warning("autofix: trying to fix sub-task without parent by converting to it to bug")
                data['fields']['issuetype'] = {"name": "Bug"}
            if "The summary is invalid because it contains newline characters." in error_list:
                logging.warning("autofix: trying to fix newline in summary")
                data['fields']['summary'] = self.fields.summary.replace("/n", "")
            for error in error_list:
                if re.search(u"^User '(.*)' was not found in the system\.", error, re.U):
                    m = re.search(u"^User '(.*)' was not found in the system\.", error, re.U)
                    if m:
                        user = m.groups()[0]
                    else:
                        raise NotImplemented()
                if re.search("^User '(.*)' does not exist\.", error):
                    m = re.search("^User '(.*)' does not exist\.", error)
                    if m:
                        user = m.groups()[0]
                    else:
                        raise NotImplemented()

            if user:
                logging.warning("Trying to add missing orphan user '%s' in order to complete the previous failed operation." % user)
                jira.add_user(user, 'noreply@example.com', 10100, active=False)
                # if 'assignee' not in data['fields']:
                #    logging.warning("autofix: setting assignee to '%s' and retrying the update." % self._options['autofix'])
                #    data['fields']['assignee'] = {'name': self._options['autofix']}
            # EXPERIMENTAL --->
            # import grequests
            if async and 'grequests' in sys.modules:
                if not hasattr(self._session, '_async_jobs'):
                    self._session._async_jobs = set()
                self._session._async_jobs.add(grequests.put(self.self, headers={'content-type': 'application/json'}, data=json.dumps(data)))
            else:
                r = self._session.put(self.self, headers={'content-type': 'application/json'}, data=json.dumps(data))
                raise_on_error(r)
        self._load(self.self)

    def delete(self, params=None):
        """
        Delete this resource from the server, passing the specified query parameters. If this resource doesn't support
        ``DELETE``, a :py:exc:`.JIRAError` will be raised; subclasses that specialize this method will only raise errors
        in case of user error.
        """

        if self._options['async']:
            if not hasattr(self._session, '_async_jobs'):
                self._session._async_jobs = set()
            self._session._async_jobs.add(grequests.delete(self.self, params=params))
        else:
            r = self._session.delete(self.self, params=params)
            raise_on_error(r)

    def _load(self, url, headers=None, params=None):
        r = self._session.get(url, headers=headers, params=params)
        raise_on_error(r)

        self._parse_raw(json.loads(r.text))

    def _parse_raw(self, raw):
        self.raw = raw
        dict2resource(raw, self, self._options, self._session)

    def _url(self, ids):
        url = '{server}/rest/{rest_path}/{rest_api_version}/'.format(**self._options)
        url += self._resource.format(*ids)
        return url

    def _default_headers(self, user_headers):
        result = dict(user_headers)
        result['accept'] = 'application/json'
        return result


class Attachment(Resource):

    """An issue attachment."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'attachment/{0}', options, session)
        if raw:
            self._parse_raw(raw)

    def get(self):
        """
        Returns the file content as a string.
        """
        r = self._session.get(self.content)
        raise_on_error(r)
        return r.content


class Component(Resource):

    """A project component."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'component/{0}', options, session)
        if raw:
            self._parse_raw(raw)

    def delete(self, moveIssuesTo=None):
        """
        Delete this component from the server.

        :param moveIssuesTo: the name of the component to which to move any issues this component is applied
        """
        params = {}
        if moveIssuesTo is not None:
            params['moveIssuesTo'] = moveIssuesTo

        super(Component, self).delete(params)


class CustomFieldOption(Resource):

    """An existing option for a custom issue field."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'customFieldOption/{0}', options, session)
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

    def update(self, fields=None, async=None, jira=None, **fieldargs):
        """
        Update this issue on the server.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored.

        JIRA projects may contain many different issue types. Some issue screens have different requirements for
        fields in an issue. This information is available through the :py:meth:`.JIRA.editmeta` method. Further examples
        are available here: https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+Example+-+Edit+issues

        :param fields: a dict containing field names and the values to use; if present, all other keyword arguments\
        will be ignored
        """
        data = {}
        if fields is not None:
            data['fields'] = fields
        else:
            fields_dict = {}
            for field in fieldargs:
                fields_dict[field] = fieldargs[field]
            data['fields'] = fields_dict

        super(Issue, self).update(async=async, jira=jira, **data)

    def add_field_value(self, field, value):
        """
        Add a value to a field that supports multiple values, without resetting the existing values.

        This should work with: labels, multiple checkbox lists, multiple select
        """
        field = self.instance.resolve_fields(field)
        self.update({"update": {field: [{"add": value}]}})

    def delete(self, deleteSubtasks=False):
        """
        Delete this issue from the server.

        :param deleteSubtasks: if the issue has subtasks, this argument must be set to true for the call to succeed.
        """
        super(Issue, self).delete(params={'deleteSubtasks': deleteSubtasks})

    def permalink(self):
        """
        Gets the URL of the issue, the browsable one not the REST one.

        :return: URL of the issue
        """
        return "%s/browse/%s" % (self._options['server'], str(self))


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

    def update(self, object, globalId=None, application=None, relationship=None):
        """
        Update a RemoteLink. 'object' is required and should be

        For definitions of the allowable fields for 'object' and the keyword arguments 'globalId', 'application' and
        'relationship', see https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+for+Remote+Issue+Links.

        :param object: the link details to add (see the above link for details)
        :param globalId: unique ID for the link (see the above link for details)
        :param application: application information for the link (see the above link for details)
        :param relationship: relationship description for the link (see the above link for details)
        """
        data = {
            'object': object
        }
        if globalId is not None:
            data['globalId'] = globalId
        if application is not None:
            data['application'] = application
        if relationship is not None:
            data['relationship'] = relationship

        super(RemoteLink, self).update(**data)


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

    def delete(self, username):
        """
        Remove the specified user from the watchers list.
        """
        super(Watchers, self).delete(params={'username': username})


class Worklog(Resource):

    """Worklog on an issue."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'issue/{0}/worklog/{1}', options, session)
        if raw:
            self._parse_raw(raw)

    def delete(self, adjustEstimate=None, newEstimate=None, increaseBy=None):
        """
        Delete this worklog entry from its associated issue.

        :param adjustEstimate: one of ``new``, ``leave``, ``manual`` or ``auto``. ``auto`` is the default and adjusts\
        the estimate automatically. ``leave`` leaves the estimate unchanged by this deletion.
        :param newEstimate: combined with ``adjustEstimate=new``, set the estimate to this value
        :param increaseBy: combined with ``adjustEstimate=manual``, increase the remaining estimate by this amount
        """
        params = {}
        if adjustEstimate is not None:
            params['adjustEstimate'] = adjustEstimate
        if newEstimate is not None:
            params['newEstimate'] = newEstimate
        if increaseBy is not None:
            params['increaseBy'] = increaseBy

        super(Worklog, self).delete(params)


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

    def update(self, users=None, groups=None):
        """
        Add the specified users or groups to this project role. One of ``users`` or ``groups`` must be specified.

        :param users: a user or users to add to the role
        :type users: string, list or tuple
        :param groups: a group or groups to add to the role
        :type groups: string, list or tuple
        """
        if users is not None and isinstance(users, string_types):
            users = (users,)
        if groups is not None and isinstance(groups, string_types):
            groups = (groups,)

        data = {
            'id': self.id,
            'categorisedActors': {
                'atlassian-user-role-actor': users,
                'atlassian-group-role-actor': groups
            }
        }

        super(Role, self).update(**data)


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

    def delete(self, moveFixIssuesTo=None, moveAffectedIssuesTo=None):
        """
        Delete this project version from the server. If neither of the arguments are specified, the version is
        removed from all issues it is attached to.

        :param moveFixIssuesTo: in issues for which this version is a fix version, add this argument version to the fix\
        version list
        :param moveAffectedIssuesTo: in issues for which this version is an affected version, add this argument version\
        to the affected version list
        """
        params = {}
        if moveFixIssuesTo is not None:
            params['moveFixIssuesTo'] = moveFixIssuesTo
        if moveAffectedIssuesTo is not None:
            params['moveAffectedIssuesTo'] = moveAffectedIssuesTo

        super(Version, self).delete(params)

    def update(self, **args):
        """
        Update this project version from the server. It is prior used to archive
        versions
        """
        data = {}
        for field in args:
            data[field] = args[field]

        super(Version, self).update(**data)


# GreenHopper


class GreenHopperResource(Resource):

    """A generic GreenHopper resource."""

    def __init__(self, path, options, session, raw):
        Resource.__init__(self, path, options, session)
        if raw:
            self._parse_raw(raw)

    def _url(self, ids):
        url = '{server}/rest/greenhopper/1.0/'.format(**self._options)
        url += self._resource.format(*ids)
        return url


class Sprint(GreenHopperResource):

    """A GreenHopper sprint."""

    def __init__(self, options, session, raw):
        GreenHopperResource.__init__(self, 'sprints/{0}', options, session, raw)
        if raw:
            self._parse_raw(raw)


class Board(GreenHopperResource):

    """A GreenHopper board."""

    def __init__(self, options, session, raw):
        GreenHopperResource.__init__(self, 'views/{0}', options, session, raw)
        if raw:
            self._parse_raw(raw)

# Utilities


def dict2resource(raw, top=None, options=None, session=None):
    """
    Recursively walks a dict structure, transforming the properties into attributes
    on a new ``Resource`` object of the appropriate type (if a ``self`` link is present)
    or a ``PropertyHolder`` object (if no ``self`` link is present).
    """
    if top is None:
        top = type(str('PropertyHolder'), (object,), raw)

    seqs = tuple, list, set, frozenset
    for i, j in iteritems(raw):
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

resource_class_map = {
    # JIRA specific resources
    r'attachment/[^/]+$': Attachment,
    r'component/[^/]+$': Component,
    r'customFieldOption/[^/]+$': CustomFieldOption,
    r'dashboard/[^/]+$': Dashboard,
    r'filter/[^/]$': Filter,
    r'issue/[^/]+$': Issue,
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
    # GreenHopper specific resources
    r'sprints/[^/]+$': Sprint,
    r'views/[^/]+$': Board,
}


def cls_for_resource(resource_literal):
    for resource in resource_class_map:
        if re.search(resource, resource_literal):
            return resource_class_map[resource]
    else:
        # Generic Resource without specialized update/delete behavior
        return Resource
