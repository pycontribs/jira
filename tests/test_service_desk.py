#!/usr/bin/env python
from __future__ import print_function
import inspect
import logging
import os
import platform
import sys
from time import sleep

from flaky import flaky
import pytest
import requests

from tests.jira_test_manager import JiraTestManager


# _non_parallel is used to prevent some tests from failing due to concurrency
# issues because detox, Travis or Jenkins can run test in parallel for multiple
# python versions.
# The current workaround is to run these problematic tests only on py27

_non_parallel = True
if platform.python_version() < '3':
    _non_parallel = False

    try:
        import unittest2 as unittest
    except ImportError:
        import pip

        if hasattr(sys, 'real_prefix'):
            pip.main(['install', '--upgrade', 'unittest2'])
        else:
            pip.main(['install', '--upgrade', '--user', 'unittest2'])
        import unittest2 as unittest
else:
    import unittest

cmd_folder = os.path.abspath(os.path.join(os.path.split(inspect.getfile(
    inspect.currentframe()))[0], ".."))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

import jira  # noqa
from jira import Role, Issue, JIRA, JIRAError, Project  # noqa
from jira.resources import Resource, cls_for_resource   # noqa

TEST_ROOT = os.path.dirname(__file__)
TEST_ICON_PATH = os.path.join(TEST_ROOT, 'icon.png')
TEST_ATTACH_PATH = os.path.join(TEST_ROOT, 'tests.py')

OAUTH = False
CONSUMER_KEY = 'oauth-consumer'
KEY_CERT_FILE = '/home/bspeakmon/src/atlassian-oauth-examples/rsa.pem'
KEY_CERT_DATA = None
try:
    with open(KEY_CERT_FILE, 'r') as cert:
        KEY_CERT_DATA = cert.read()
    OAUTH = True
except Exception:
    pass

if 'CI_JIRA_URL' in os.environ:
    not_on_custom_jira_instance = pytest.mark.skipif(True, reason="Not applicable for custom JIRA instance")
    logging.info('Picked up custom JIRA engine.')
else:
    def noop(arg):
        return arg
    not_on_custom_jira_instance = noop


def jira_servicedesk_detection():
    if 'CI_JIRA_URL' in os.environ:
        url = os.environ['CI_JIRA_URL']
    else:
        url = 'https://pycontribs.atlassian.net'
    url += '/rest/servicedeskapi/info'
    return requests.get(url).status_code != 200

jira_servicedesk = pytest.mark.skipif(jira_servicedesk_detection(), reason="JIRA Service Desk is not available.")


@flaky
@jira_servicedesk
class ServiceDeskTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = self.test_manager.jira_admin
        self.desk = self.jira.desk
        self.test_fullname_a = "TestCustomerFullName %s" % self.test_manager.project_a
        self.test_email_a = "test_customer_%s@example.com" % self.test_manager.project_a
        self.test_fullname_b = "TestCustomerFullName %s" % self.test_manager.project_b
        self.test_email_b = "test_customer_%s@example.com" % self.test_manager.project_b
        self.test_organization_name_a = "test_organization_%s" % self.test_manager.project_a
        self.test_organization_name_b = "test_organization_%s" % self.test_manager.project_b

    def test_create_and_delete_customer(self):
        try:
            self.jira.delete_user(self.test_email_a)
        except JIRAError:
            pass

        customer = self.desk.create_customer(self.test_email_a, self.test_fullname_a)
        self.assertEqual(customer.emailAddress, self.test_email_a)
        self.assertEqual(customer.displayName, self.test_fullname_a)

        result = self.jira.delete_user(self.test_email_a)
        self.assertTrue(result)

    def test_get_servicedesk_info(self):
        result = self.desk.servicedesk_info()
        self.assertNotEqual(result, False)

    def test_create_and_delete_organization(self):
        organization = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization.name, self.test_organization_name_a)

        result = self.desk.delete_organization(organization.id)
        self.assertTrue(result)

    def test_get_organization(self):
        organization = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization.name, self.test_organization_name_a)

        result = self.desk.organization(organization.id)
        self.assertEqual(result.id, organization.id)
        self.assertEqual(result.name, self.test_organization_name_a)

        result = self.desk.delete_organization(organization.id)
        self.assertTrue(result)

    def test_add_users_to_organization(self):
        organization = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization.name, self.test_organization_name_a)

        try:
            self.jira.delete_user(self.test_email_a)
        except JIRAError:
            pass

        try:
            self.jira.delete_user(self.test_email_b)
        except JIRAError:
            pass

        customer_a = self.desk.create_customer(self.test_email_a, self.test_fullname_a)
        self.assertEqual(customer_a.emailAddress, self.test_email_a)
        self.assertEqual(customer_a.displayName, self.test_fullname_a)

        customer_b = self.desk.create_customer(self.test_email_b, self.test_fullname_b)
        self.assertEqual(customer_b.emailAddress, self.test_email_b)
        self.assertEqual(customer_b.displayName, self.test_fullname_b)

        result = self.desk.add_users_to_organization(organization.id, [self.test_email_a, self.test_email_b])
        self.assertTrue(result)

        result = self.jira.delete_user(self.test_email_a)
        self.assertTrue(result)

        result = self.jira.delete_user(self.test_email_b)
        self.assertTrue(result)

        result = self.desk.delete_organization(organization.id)
        self.assertTrue(result)

    def test_remove_users_from_organization(self):
        organization = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization.name, self.test_organization_name_a)

        try:
            self.jira.delete_user(self.test_email_a)
        except JIRAError:
            pass

        try:
            self.jira.delete_user(self.test_email_b)
        except JIRAError:
            pass

        customer_a = self.desk.create_customer(self.test_email_a, self.test_fullname_a)
        self.assertEqual(customer_a.emailAddress, self.test_email_a)
        self.assertEqual(customer_a.displayName, self.test_fullname_a)

        customer_b = self.desk.create_customer(self.test_email_b, self.test_fullname_b)
        self.assertEqual(customer_b.emailAddress, self.test_email_b)
        self.assertEqual(customer_b.displayName, self.test_fullname_b)

        result = self.desk.add_users_to_organization(organization.id, [self.test_email_a, self.test_email_b])
        self.assertTrue(result)

        result = self.desk.remove_users_from_organization(organization.id, [self.test_email_a, self.test_email_b])
        self.assertTrue(result)

        result = self.jira.delete_user(self.test_email_a)
        self.assertTrue(result)

        result = self.jira.delete_user(self.test_email_b)
        self.assertTrue(result)

        result = self.desk.delete_organization(organization.id)
        self.assertTrue(result)

    def test_get_organizations(self):
        organization_a = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization_a.name, self.test_organization_name_a)

        organization_b = self.desk.create_organization(self.test_organization_name_b)
        self.assertEqual(organization_b.name, self.test_organization_name_b)

        organizations = self.desk.organizations(0, 1)
        self.assertEqual(len(organizations), 1)

        result = self.desk.delete_organization(organization_a.id)
        self.assertTrue(result)

        result = self.desk.delete_organization(organization_b.id)
        self.assertTrue(result)

    def test_get_users_in_organization(self):
        organization = self.desk.create_organization(self.test_organization_name_a)
        self.assertEqual(organization.name, self.test_organization_name_a)

        try:
            self.jira.delete_user(self.test_email_a)
        except JIRAError:
            pass

        try:
            self.jira.delete_user(self.test_email_b)
        except JIRAError:
            pass

        customer_a = self.desk.create_customer(self.test_email_a, self.test_fullname_a)
        self.assertEqual(customer_a.emailAddress, self.test_email_a)
        self.assertEqual(customer_a.displayName, self.test_fullname_a)

        customer_b = self.desk.create_customer(self.test_email_b, self.test_fullname_b)
        self.assertEqual(customer_b.emailAddress, self.test_email_b)
        self.assertEqual(customer_b.displayName, self.test_fullname_b)

        result = self.desk.add_users_to_organization(organization.id, [self.test_email_a, self.test_email_b])
        self.assertTrue(result)

        result = self.desk.get_users_from_organization(organization.id)
        self.assertEqual(len(result), 2)

        result = self.jira.delete_user(self.test_email_a)
        self.assertTrue(result)

        result = self.jira.delete_user(self.test_email_b)
        self.assertTrue(result)

        result = self.desk.delete_organization(organization.id)
        self.assertTrue(result)

    def test_service_desks(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

    def test_servicedesk(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        service_desk = self.desk.service_desk(service_desks[0].id)
        self.assertEqual(service_desk.id, service_desks[0].id)

    def test_request_types(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

    def test_request_type(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        request_type = self.desk.request_type(service_desks[0].id, request_types[0].id)
        self.assertEqual(request_type.id, request_types[0].id)
        self.assertEqual(request_type.name, request_types[0].name)

    def test_request_type_by_name(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        request_type_by_name = self.desk.request_type_by_name(service_desks[0].id, request_types[0].name)
        self.assertEqual(request_types[0].id, request_type_by_name.id)
        self.assertEqual(request_types[0].name, request_type_by_name.name)

    def test_create_and_delete_customer_request_with_prefetch(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request = self.desk.create_request(fields, prefetch=True)

        self.jira.delete_issue(request.id)

        self.assertIsNotNone(request.id)
        self.assertIsNotNone(request.key)
        self.assertEqual(request.fields.summary, "Request summary")
        self.assertEqual(request.fields.description, "Request description")

    def test_create_and_delete_customer_request_without_prefetch(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request = self.desk.create_request(fields, prefetch=False)

        self.jira.delete_issue(request.id)

        self.assertIsNotNone(request.id)
        self.assertIsNotNone(request.key)
        self.assertEqual(request.fields.summary, "Request summary")
        self.assertEqual(request.fields.description, "Request description")

    def test_get_customer_request_by_key_or_id(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request = self.desk.create_request(fields, prefetch=False)

        expand = 'serviceDesk,requestType,participant,sla,status'
        request_by_key = self.desk.request(request.key, expand=expand)

        self.assertEqual(request.id, request_by_key.id)
        self.assertEqual(request.key, request_by_key.key)
        self.assertEqual(request_by_key.fields.summary, "Request summary")
        self.assertEqual(request_by_key.fields.description, "Request description")

        expand = 'serviceDesk,requestType,participant,sla,status'
        request_by_id = self.desk.request(request.id, expand=expand)

        self.jira.delete_issue(request.id)

        self.assertEqual(request.id, request_by_id.id)
        self.assertEqual(request.key, request_by_id.key)
        self.assertEqual(request_by_id.fields.summary, "Request summary")
        self.assertEqual(request_by_id.fields.description, "Request description")

    def test_get_my_customer_requests(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request1 = self.desk.create_request(fields, prefetch=False)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_ADMIN,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request2 = self.desk.create_request(fields, prefetch=False)

        result = self.desk.my_customer_requests(request_ownership='OWNED_REQUESTS',
                                                servicedesk_id=int(service_desks[0].id),
                                                request_type_id=int(request_types[0].id))
        count = 0
        requests = (request1.id, request2.id)
        for i in result:
            if i.id in requests:
                count += 1

        self.assertEqual(count, 1)

        result = self.desk.my_customer_requests(request_ownership='PARTICIPATED_REQUESTS',
                                                servicedesk_id=int(service_desks[0].id),
                                                request_type_id=int(request_types[0].id))
        count = 0
        requests_list = (request1.id, request2.id)
        for i in result:
            if i.id in requests_list:
                count += 1

        self.jira.delete_issue(request1.id)
        self.jira.delete_issue(request2.id)

        self.assertEqual(count, 0)

    def test_request_comments(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request = self.desk.create_request(fields, prefetch=False)

        self.jira.add_comment(request.id, "Public comment #1", is_internal=False)
        self.jira.add_comment(request.id, "Internal comment #1", is_internal=True)
        self.jira.add_comment(request.id, "Public comment #2", is_internal=False)
        self.jira.add_comment(request.id, "Public comment #3", is_internal=False)
        sleep(1)
        public_comments = self.desk.request_comments(request.id, public=True, internal=False)
        internal_comments = self.desk.request_comments(request.id, public=False, internal=True)
        all_comments = self.desk.request_comments(request.id)

        self.assertEqual(len(public_comments), 3)
        self.assertEqual(len(internal_comments), 1)
        self.assertEqual(len(all_comments), 4)

        for comment in public_comments:
            self.assertEqual(comment.public, True)

        for comment in internal_comments:
            self.assertEqual(comment.public, False)

        self.jira.delete_issue(request.id)

    def test_create_attachment(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        request_types = self.desk.request_types(service_desks[0].id)
        self.assertGreater(len(request_types), 0)

        fields = {
            "serviceDeskId": int(service_desks[0].id),
            "requestTypeId": int(request_types[0].id),
            "raiseOnBehalfOf": self.test_manager.CI_JIRA_USER,
            "requestFieldValues": {
                "summary": "Request summary",
                "description": "Request description"
            }
        }
        request = self.desk.create_request(fields)

        tmp_attachment = self.desk.attach_temporary_file(service_desks[0].id, open(TEST_ICON_PATH, 'rb'), "test.png")

        self.assertEqual(len(tmp_attachment.temporaryAttachments), 1)
        self.assertEqual(tmp_attachment.temporaryAttachments[0].fileName, 'test.png')

        request_attachment = self.desk.servicedesk_attachment(request.id, tmp_attachment, is_public=False,
                                                              comment='Comment text')
        self.jira.delete_issue(request.id)

        self.assertEqual(request_attachment.comment.body, 'Comment text\n\n!test.png|thumbnail!')

        if hasattr(request_attachment.attachments, 'values'):
            # For Jira Servicedesk Cloud
            self.assertGreater(len(request_attachment.attachments.values), 0)
            self.assertEqual(request_attachment.attachments.values[0].filename, 'test.png')
            self.assertGreater(request_attachment.attachments.values[0].size, 0)
        else:
            # For Jira Servicedesk Server
            self.assertGreater(len(request_attachment.attachments), 0)
            self.assertEqual(request_attachment.attachments[0].filename, 'test.png')
            self.assertGreater(request_attachment.attachments[0].size, 0)

    def test_attach_temporary_file(self):
        service_desks = self.desk.service_desks()
        self.assertGreater(len(service_desks), 0)

        tmp_attachment = self.desk.attach_temporary_file(service_desks[0].id, open(TEST_ICON_PATH, 'rb'), "test.png")

        self.assertEqual(len(tmp_attachment.temporaryAttachments), 1)
        self.assertEqual(tmp_attachment.temporaryAttachments[0].fileName, 'test.png')

    def test_create_customer_request(self):
        try:
            self.jira.create_project('TESTSD', template_name='IT Service Desk')
        except JIRAError:
            pass
        service_desk = self.desk.service_desks()[0]
        request_type = self.desk.request_types(service_desk.id)[0]

        request = self.desk.create_customer_request(dict(
            serviceDeskId=service_desk.id,
            requestTypeId=int(request_type.id),
            requestFieldValues=dict(
                summary='Ticket title here',
                description='Ticket body here'
            )
        ))

        self.assertEqual(request.fields.summary, 'Ticket title here')
        self.assertEqual(request.fields.description, 'Ticket body here')


if __name__ == '__main__':

    # when running tests we expect various errors and we don't want to display them by default
    logging.getLogger("requests").setLevel(logging.FATAL)
    logging.getLogger("urllib3").setLevel(logging.FATAL)
    logging.getLogger("jira").setLevel(logging.FATAL)

    # j = JIRA("https://issues.citrite.net")
    # print(j.session())

    dirname = "test-reports-%s%s" % (sys.version_info[0], sys.version_info[1])
    unittest.main()
    # pass
