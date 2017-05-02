#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

"""
This module implements a friendly (well, friendlier) interface between the raw JSON
responses from JIRA ServiceDesk and the Resource/dict abstractions provided by this library
"""

import json
import logging
import os
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):

        def emit(self, record):
            pass
import warnings

from jira.exceptions import JIRAError

from jira.resources import Comment
from jira.resources import Customer
from jira.resources import Issue
from jira.resources import Organization
from jira.resources import Request
from jira.resources import RequestAttachment
from jira.resources import RequestTemporaryAttachment
from jira.resources import RequestType
from jira.resources import ServiceDesk
from jira.resources import ServiceDeskInfo
from jira.resources import User

from jira.utils import CaseInsensitiveDict
from jira.utils import json_loads

from six import integer_types
from six import string_types

try:
    # noinspection PyUnresolvedReferences
    from requests_toolbelt import MultipartEncoder
except ImportError:
    pass

logging.getLogger('jira').addHandler(NullHandler())


class JiraServiceDesk(object):
    """Service desk related functionality"""

    def __init__(self, jira):
        self._jira = jira

    def supports_service_desk(self):
        url = self._options['server'] + '/rest/servicedeskapi/info'
        headers = {'X-ExperimentalApi': 'opt-in'}
        try:
            r = self._jira._session.get(url, headers=headers)
            return r.status_code == 200
        except JIRAError:
            return False

    def create_customer(self, email, fullname):
        """Creates a customer that is not associated with a service desk project.

        :param email: email of the user (customer) to create
        :param fullname: user full name
        :return Customer
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/customer'
        headers = {'X-ExperimentalApi': 'opt-in'}
        result = self._jira._session.post(url, headers=headers, data=json.dumps({'email': email, 'fullName': fullname}))
        if result.status_code != 201:
            raise JIRAError(result.status_code, request=result)
        return Customer(self._jira._options, self._jira._session, raw=json_loads(result))

    def servicedesk_info(self):
        """Returns runtime information about JIRA Service Desk.

        :return ServiceDeskInfo
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/info'
        result = self._jira._session.get(url)
        if result.status_code != 200:
            raise JIRAError(result.status_code, request=result)
        return ServiceDeskInfo(self._jira._options, self._jira._session, raw=json_loads(result))

    def create_organization(self, name):
        """Creates an organization

        :param name: name of the organization to create
        :return Organization
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/organization'
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        result = self._jira._session.post(url, headers=headers, data=json.dumps({'name': name}))
        if result.status_code != 201:
            raise JIRAError(result.status_code, request=result)
        return Organization(self._jira._options, self._jira._session, raw=json_loads(result))

    def delete_organization(self, organization_id):
        """Delete organization

        :param organization_id: ID of the organization to delete
        :return boolean
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/organization/%i' % int(organization_id)
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        result = self._jira._session.delete(url, headers=headers)
        if result.status_code != 204:
            raise JIRAError(result.status_code, request=result)
        return True

    def organization(self, id):
        """Get an organization for a given organization ID

        :param id: ID of the organization to get
        :return Organization
        """
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        organization = Organization(self._jira._options, self._jira._session)
        organization.find(id, headers=headers)
        return organization

    def organizations(self, start=0, limit=50):
        """Returns a list of organizations in the JIRA instance.

        If the user is not an agent, the resource returns a list of organizations the user is a member of.

        :param start: index of the first organization to return.
        :param limit: maximum number of organizations to return. If limit evaluates as False, it will try to get all
        items in batches.
        :return list of Organization resources
        """
        params = {'start': start, 'limit': limit}
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        base = self._jira._options['server'] + '/rest/servicedeskapi/organization'
        return self._jira._fetch_pages(Organization,
                                       'values',
                                       'organization',
                                       params=params,
                                       headers=headers,
                                       base=base)

    def add_users_to_organization(self, organization_id, usernames):
        """Add users to organization

        :param organization_id: organization ID
        :param usernames: list with usernames
        :return boolean
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/organization/%i/user' % int(organization_id)
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        params = {}
        if isinstance(usernames, list):
            params['usernames'] = usernames
        else:
            params['usernames'] = [usernames]
        result = self._jira._session.post(url, headers=headers, data=json.dumps(params))
        if result.status_code != 204:
            raise JIRAError(result.status_code, request=result)
        return True

    def remove_users_from_organization(self, organization_id, usernames):
        """Remove users from organization

        :param organization_id: organization ID
        :param usernames: list with usernames
        :return boolean
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/organization/%i/user' % int(organization_id)
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        params = {}
        if isinstance(usernames, list):
            params['usernames'] = usernames
        else:
            params['usernames'] = [usernames]
        result = self._jira._session.delete(url, headers=headers, data=json.dumps(params))
        if result.status_code != 204:
            raise JIRAError(result.status_code, request=result)
        return True

    def get_users_from_organization(self, organization_id, start=0, limit=50):
        """Returns a list of users in organization.

        :param organization_id: organization ID
        :param start: index of the first user to return.
        :param limit: maximum number of organizations to return.
                      If limit evaluates as False, it will try to get all items in batches.
        """
        params = {'start': start, 'limit': limit}
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        base = self._jira._options['server'] + '/rest/servicedeskapi/organization/%i/user' % int(organization_id)
        return self._jira._fetch_pages(User,
                                       'values',
                                       None,
                                       params=params,
                                       headers=headers,
                                       base=base)

    def service_desks(self, start=0, limit=50):
        """Returns a list of service desks

        :param start: index of the first service desk to return.
        :param limit: maximum number of service desks to return.
                      If limit evaluates as False, it will try to get all items in batches.
        """
        params = {'start': start, 'limit': limit}
        base = self._jira._options['server'] + '/rest/servicedeskapi/servicedesk'
        return self._jira._fetch_pages(ServiceDesk,
                                       'values',
                                       None,
                                       params=params,
                                       base=base)

    def service_desk(self, id):
        """Returns the service desk for a given service desk Id.

        :param id: servicedesk ID
        :return: Servicedesk
        """
        service_desk = ServiceDesk(self._jira._options, self._jira._session)
        service_desk.find(id)
        return service_desk

    def create_customer_request(self, fields=None, prefetch=True, **fieldargs):
        """Create a new customer request and return an issue Resource for it.

        Deprecated method. Use "create_request" instead.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored.

        By default, the client will immediately reload the issue Resource created by this method in order to return
        a complete Issue object to the caller; this behavior can be controlled through the 'prefetch' argument.

        JIRA projects may contain many different issue types. Some issue screens have different requirements for
        fields in a new issue. This information is available through the 'createmeta' method. Further examples are
        available here: https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+Example+-+Create+Issue

        :param fields: a dict containing field names and the values to use. If present, all other keyword arguments
            will be ignored
        :param prefetch: whether to reload the created issue Resource so that all of its data is present in the value
            returned from this method
        """

        warnings.warn("Use 'create_request' method instead", DeprecationWarning)

        if isinstance(fields['serviceDeskId'], ServiceDesk):
            fields['serviceDeskId'] = fields['serviceDeskId'].id

        if isinstance(fields['requestTypeId'], string_types):
            fields['requestTypeId'] = self.request_type_by_name(fields['serviceDeskId'], fields['requestTypeId']).id

        url = self._jira._options['server'] + '/rest/servicedeskapi/request'
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        result = self._jira._session.post(url, headers=headers, data=json.dumps(fields))

        raw_issue_json = json_loads(result)
        if 'issueKey' not in raw_issue_json:
            raise JIRAError(result.status_code, request=result)
        if prefetch:
            return self._jira.issue(raw_issue_json['issueKey'])
        else:
            return Issue(self._jira._options, self._jira._session, raw=raw_issue_json)

    def create_request(self, fields=None, prefetch=True, **fieldargs):
        """Create a new customer request and return an issue Resource for it.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored.

        By default, the client will immediately reload the issue Resource created by this method in order to return
        a complete Issue object to the caller; this behavior can be controlled through the 'prefetch' argument.

        JIRA projects may contain many different issue types. Some issue screens have different requirements for
        fields in a new issue. This information is available through the 'createmeta' method. Further examples are
        available here: https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+Example+-+Create+Issue

        :param fields: a dict containing field names and the values to use. If present, all other keyword arguments
            will be ignored
        :param prefetch: whether to reload the created issue Resource so that all of its data is present in the value
            returned from this method
        :return: Request
        """

        if isinstance(fields['serviceDeskId'], ServiceDesk):
            fields['serviceDeskId'] = fields['serviceDeskId'].id

        if isinstance(fields['requestTypeId'], string_types):
            fields['requestTypeId'] = self.request_type_by_name(fields['serviceDeskId'], fields['requestTypeId']).id

        url = self._jira._options['server'] + '/rest/servicedeskapi/request'
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        result = self._jira._session.post(url, headers=headers, data=json.dumps(fields))

        raw_issue_json = json_loads(result)
        if 'issueId' not in raw_issue_json:
            raise JIRAError(result.status_code, request=result)
        if prefetch:
            return self.request(raw_issue_json['issueId'])
        else:
            return Request(self._jira._options, self._jira._session, raw=raw_issue_json)

    def request(self, id, expand=None):
        """Get an issue Resource from the server.

        :param id: ID or key of the customer request (issue) to get
        :param expand: This is a multi-value parameter indicating which properties of the customer request to expand:
            serviceDesk - Return additional details for each service desk in the response.
            requestType - Return additional details for each request type in the response.
            participant - Return the participant details, if any, for each customer request in the response.
            sla - Return the SLA information on the given request.
            status - Return the status transitions, in chronological order, for each customer request in the response.
        :return: list of Request resources
        """
        params = {}
        if expand is not None:
            params['expand'] = expand

        request = Request(self._jira._options, self._jira._session)
        request.find(id, params=params)
        return request

    def my_customer_requests(self,
                             search_term=None,
                             request_ownership=None,
                             request_status=None,
                             servicedesk_id=None,
                             request_type_id=None,
                             expand=None,
                             start=0, limit=50):
        """Returns all customer requests for the user that is executing the query.

        :param search_term: (string) Filters results to customer requests where the issue summary matches the
        searchTerm. You can use wildcards in the searchTerm.
        :param request_ownership: (string) Filters results to customer requests where the user is the creator
        and/or participant:
            - OWNED_REQUESTS - Only return customer requests where the user is the creator.
            - PARTICIPATED_REQUESTS - Only return customer requests where the user is a participant.
            - ALL_REQUESTS - Return customer requests where the user is the creator or a participant.
        :param request_status: (string) Filters results to customer requests that are resolved, unresolved,
        or either of the two:
            - CLOSED_REQUESTS - Only return customer requests that are resolved.
            - OPEN_REQUESTS - Only return customer requests that are unresolved.
            - ALL_REQUESTS - Returns customer requests that are either resolved or unresolved.
        :param servicedesk_id: (int) Filters results to customer requests from a specific service desk.
        :param request_type_id: (int) Filters results to customer requests of a specific request type.
        You must also specify the serviceDeskID for the service desk that the request type belongs to.
        :param expand: (string) This is a multi-value parameter indicating which properties of the customer request
        to expand:
            - serviceDesk - Return additional details for each service desk in the response.
            - requestType - Return additional details for each request type in the response.
            - participant - Return the participant details, if any, for each customer request in the response.
            - sla - Return the SLA information on the given request.
            - status - Return the status transitions, in chronological order, for each customer request in the response.
        :param start: (int) The starting index of the returned objects. Base index: 0.
        :param limit: (int) The maximum number of items to return per page. Default: 50.
        :return: list of Request resources
        """
        params = {'start': start, 'limit': limit}
        if isinstance(search_term, string_types):
            params['searchTerm'] = search_term
        if isinstance(request_ownership, string_types):
            params['requestOwnership'] = request_ownership
        if isinstance(request_status, string_types):
            params['requestStatus'] = request_status
        if isinstance(servicedesk_id, integer_types):
            params['serviceDeskId'] = servicedesk_id
        if isinstance(request_type_id, integer_types):
            params['requestTypeId'] = request_type_id
        if isinstance(expand, string_types):
            params['expand'] = expand
        base = self._jira._options['server'] + '/rest/servicedeskapi/request'
        return self._jira._fetch_pages(Request,
                                       'values',
                                       None,
                                       params=params,
                                       base=base)

    def request_comments(self, issue, public=None, internal=None, start=0, limit=50):
        """Returns all comments on a customer request, for a given request Id/key.

        :param issue: ID or key of the customer request (issue)
        :param public: Specifies whether to return public comments or not. Default: True.
        :param internal: Specifies whether to return internal comments or not. Default: true.
        :param start: (int) The starting index of the returned objects. Base index: 0.
        :param limit: (int) The maximum number of items to return per page. Default: 50.
        :return:
        """
        params = {'start': start, 'limit': limit}
        if isinstance(public, bool):
            params['public'] = public
        if isinstance(internal, bool):
            params['internal'] = internal
        base = self._jira._options['server'] + '/rest/servicedeskapi/request/%s/comment' % str(issue)
        return self._jira._fetch_pages(Comment,
                                       'values',
                                       None,
                                       params=params,
                                       base=base)

    def servicedesk_attachment(self, request_id, attachment, is_public=True, comment=None):
        """Add attachment (from RequestTemporaryAttachment) to request

        :param request_id: request ID or KEY
        :param attachment: RequestTemporaryAttachment
        :param is_public: public or internal comment
        :param comment: comment text
        :return: RequestAttachment
        """
        url = self._jira._options['server'] + '/rest/servicedeskapi/request/%s/attachment' % str(request_id)
        headers = CaseInsensitiveDict({'X-ExperimentalApi': 'opt-in'})
        params = {
            'temporaryAttachmentIds': [attachment.temporaryAttachments[0].temporaryAttachmentId],
            'public': is_public,
        }
        if comment is not None:
            params['additionalComment'] = {
                'body': comment
            }

        result = self._jira._session.post(url, headers=headers, data=json.dumps(params))

        raw_json = json_loads(result)
        if result.status_code != 201:
            raise JIRAError(result.status_code, request=result)
        return RequestAttachment(self._jira._options, self._jira._session, raw=raw_json)

    def attach_temporary_file(self, servicedesk_id, attachment, filename=None):
        """Create temporary attachment file

        :param servicedesk_id: servicedesk ID
        :param attachment: file
        :param filename: optional file name
        :return: RequestTemporaryAttachment
        """
        if isinstance(attachment, string_types):
            attachment = open(attachment, "rb")
        elif hasattr(attachment, 'read') and hasattr(attachment, 'mode') and attachment.mode != 'rb':
            logging.warning("%s was not opened in 'rb' mode, attaching file may fail." % attachment.name)

        url = self._jira._options['server'] + '/rest/servicedeskapi/servicedesk/%i/attachTemporaryFile' % int(servicedesk_id)

        fname = filename
        if not fname:
            fname = os.path.basename(attachment.name)

        def file_stream():
            return MultipartEncoder(fields={'file': (fname, attachment, 'application/octet-stream')})
        m = file_stream()

        headers = CaseInsensitiveDict({
            'content-type': m.content_type,
            'X-Atlassian-Token': 'nocheck',
            'X-ExperimentalApi': 'opt-in'
        })
        result = self._jira._session.post(url, data=m, headers=headers, retry_data=file_stream)

        if result.status_code != 201:
            raise JIRAError(result.status_code, request=result)
        return RequestTemporaryAttachment(self._jira._options, self._jira._session, raw=json_loads(result))

    def request_types(self, servicedesk_id, start=0, limit=50):
        """Returns all request types from a service desk, for a given service desk Id.

        :param service_desk: servicedesk ID or servicedesk object
        :param start: index of the first user to return.
        :param limit: maximum number of organizations to return.
                      If limit evaluates as False, it will try to get all items in batches.
        :return: list of RequestType resources
        """
        params = {'start': start, 'limit': limit}
        base = self._jira._options['server'] + '/rest/servicedeskapi/servicedesk/%i/requesttype' % int(servicedesk_id)
        return self._jira._fetch_pages(RequestType,
                                       'values',
                                       None,
                                       params=params,
                                       base=base)

    def request_type(self, servicedesk_id, id):
        """Returns a request type for a given request type Id.

        :param servicedesk_id: servicedesk ID
        :param id: request type ID
        :return: RequestType
        """
        request_type = RequestType(self._jira._options, self._jira._session)
        request_type.find((servicedesk_id, id))
        return request_type

    def request_type_by_name(self, servicedesk_id, name):
        """Return request type id by it name

        :param servicedesk_id: servicedesk ID
        :param name: request type name
        :return: RequestType
        """
        request_types = self.request_types(servicedesk_id)
        try:
            request_type = [rt for rt in request_types if rt.name == name][0]
        except IndexError:
            raise KeyError("Request type '%s' is unknown." % name)
        return request_type
