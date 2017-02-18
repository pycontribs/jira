#!/usr/bin/env python
from __future__ import print_function
import getpass
import hashlib
import inspect
import logging
import os
import pickle
import platform
import random
import re
import string
import sys
from time import sleep
import traceback

from flaky import flaky
import py
import pytest
import requests
from six import integer_types
from tenacity import retry
from tenacity import stop_after_attempt

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


def rndstr():
    return ''.join(random.sample(string.ascii_lowercase, 6))


def rndpassword():
    # generates a password of lengh 14
    s = ''.join(random.sample(string.ascii_uppercase, 5)) + \
        ''.join(random.sample(string.ascii_lowercase, 5)) + \
        ''.join(random.sample(string.digits, 2)) + \
        ''.join(random.sample('~`!@#$%^&*()_+-=[]\\{}|;\':<>?,./', 2))
    return ''.join(random.sample(s, len(s)))


def hashify(some_string, max_len=8):
    return hashlib.md5(some_string.encode('utf-8')).hexdigest()[:8].upper()


def get_unique_project_name():
    jid = ""
    user = re.sub("[^A-Z_]", "", getpass.getuser().upper())

    if user == 'TRAVIS' and 'TRAVIS_JOB_NUMBER' in os.environ:
        # please note that user underline (_) is not suppored by
        # jira even if is documented as supported.
        jid = 'T' + hashify(user + os.environ['TRAVIS_JOB_NUMBER'])
    else:
        identifier = user + \
            chr(ord('A') + sys.version_info[0]) + \
            chr(ord('A') + sys.version_info[1])
        jid = 'Z' + hashify(identifier)
    return jid


class Singleton(type):

    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class JiraTestManager(object):
    """Used to instantiate and populate the JIRA instance with data used by the unit tests.

    Attributes:
        CI_JIRA_ADMIN (str): Admin user account name.
        CI_JIRA_USER (str): Limited user account name.
        max_retries (int): number of retries to perform for recoverable HTTP errors.
    """

    # __metaclass__ = Singleton

    # __instance = None
    #
    # Singleton implementation
    # def __new__(cls, *args, **kwargs):
    #     if not cls.__instance:
    #         cls.__instance = super(JiraTestManager, cls).__new__(
    #                             cls, *args, **kwargs)
    #     return cls.__instance

    #  Implementing some kind of Singleton, to prevent test initialization
    # http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python/33201#33201
    __shared_state = {}

    @retry(stop=stop_after_attempt(2))
    def __init__(self):
        self.__dict__ = self.__shared_state

        if not self.__dict__:
            self.initialized = 0

            try:

                if 'CI_JIRA_URL' in os.environ:
                    self.CI_JIRA_URL = os.environ['CI_JIRA_URL']
                    self.max_retries = 5
                else:
                    self.CI_JIRA_URL = "https://pycontribs.atlassian.net"
                    self.max_retries = 5

                if 'CI_JIRA_ADMIN' in os.environ:
                    self.CI_JIRA_ADMIN = os.environ['CI_JIRA_ADMIN']
                else:
                    self.CI_JIRA_ADMIN = 'ci-admin'

                if 'CI_JIRA_ADMIN_PASSWORD' in os.environ:
                    self.CI_JIRA_ADMIN_PASSWORD = os.environ[
                        'CI_JIRA_ADMIN_PASSWORD']
                else:
                    self.CI_JIRA_ADMIN_PASSWORD = 'sd4s3dgec5fhg4tfsds3434'

                if 'CI_JIRA_USER' in os.environ:
                    self.CI_JIRA_USER = os.environ['CI_JIRA_USER']
                else:
                    self.CI_JIRA_USER = 'ci-user'

                if 'CI_JIRA_USER_PASSWORD' in os.environ:
                    self.CI_JIRA_USER_PASSWORD = os.environ[
                        'CI_JIRA_USER_PASSWORD']
                else:
                    self.CI_JIRA_USER_PASSWORD = 'sd4s3dgec5fhg4tfsds3434'

                self.CI_JIRA_ISSUE = os.environ.get('CI_JIRA_ISSUE', 'Bug')

                if OAUTH:
                    self.jira_admin = JIRA(oauth={
                        'access_token': 'hTxcwsbUQiFuFALf7KZHDaeAJIo3tLUK',
                        'access_token_secret': 'aNCLQFP3ORNU6WY7HQISbqbhf0UudDAf',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA})
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_admin = JIRA(self.CI_JIRA_URL, basic_auth=(self.CI_JIRA_ADMIN,
                                                                             self.CI_JIRA_ADMIN_PASSWORD),
                                               logging=False, validate=True, max_retries=self.max_retries)
                    else:
                        self.jira_admin = JIRA(self.CI_JIRA_URL, validate=True,
                                               logging=False, max_retries=self.max_retries)
                if self.jira_admin.current_user() != self.CI_JIRA_ADMIN:
                    # self.jira_admin.
                    self.initialized = 1
                    sys.exit(3)

                if OAUTH:
                    self.jira_sysadmin = JIRA(oauth={
                        'access_token': '4ul1ETSFo7ybbIxAxzyRal39cTrwEGFv',
                        'access_token_secret':
                            'K83jBZnjnuVRcfjBflrKyThJa0KSjSs2',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA}, logging=False, max_retries=self.max_retries)
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_sysadmin = JIRA(self.CI_JIRA_URL,
                                                  basic_auth=(self.CI_JIRA_ADMIN,
                                                              self.CI_JIRA_ADMIN_PASSWORD),
                                                  logging=False, validate=True, max_retries=self.max_retries)
                    else:
                        self.jira_sysadmin = JIRA(self.CI_JIRA_URL,
                                                  logging=False, max_retries=self.max_retries)

                if OAUTH:
                    self.jira_normal = JIRA(oauth={
                        'access_token': 'ZVDgYDyIQqJY8IFlQ446jZaURIz5ECiB',
                        'access_token_secret':
                            '5WbLBybPDg1lqqyFjyXSCsCtAWTwz1eD',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA})
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_normal = JIRA(self.CI_JIRA_URL,
                                                basic_auth=(self.CI_JIRA_USER,
                                                            self.CI_JIRA_USER_PASSWORD),
                                                validate=True, logging=False, max_retries=self.max_retries)
                    else:
                        self.jira_normal = JIRA(self.CI_JIRA_URL,
                                                validate=True, logging=False, max_retries=self.max_retries)

                # now we need some data to start with for the tests

                # jira project key is max 10 chars, no letter.
                # [0] always "Z"
                # [1-6] username running the tests (hope we will not collide)
                # [7-8] python version A=0, B=1,..
                # [9] A,B -- we may need more than one project

                """ `jid` is important for avoiding concurency problems when
                executing tests in parallel as we have only one test instance.

                jid length must be less than 9 characters because we may append
                another one and the JIRA Project key length limit is 10.

                Tests run in parallel:
                * git branches master or developer, git pr or developers running
                  tests outside Travis
                * Travis is using "Travis" username

                https://docs.travis-ci.com/user/environment-variables/
                """

                self.jid = get_unique_project_name()

                self.project_a = self.jid + 'A'  # old XSS
                self.project_a_name = "Test user=%s key=%s A" \
                                      % (getpass.getuser(), self.project_a)
                self.project_b = self.jid + 'B'  # old BULK
                self.project_b_name = "Test user=%s key=%s B" \
                                      % (getpass.getuser(), self.project_b)

                # TODO(ssbarnea): find a way to prevent SecurityTokenMissing for On Demand
                # https://jira.atlassian.com/browse/JRA-39153
                try:
                    self.jira_admin.project(self.project_a)
                except Exception as e:
                    logging.warning(e)
                    pass
                else:
                    try:
                        self.jira_admin.delete_project(self.project_a)
                    except Exception as e:
                        pass

                try:
                    self.jira_admin.project(self.project_b)
                except Exception as e:
                    logging.warning(e)
                    pass
                else:
                    try:
                        self.jira_admin.delete_project(self.project_b)
                    except Exception as e:
                        pass

                # wait for the project to be deleted
                for i in range(1, 20):
                    try:
                        self.jira_admin.project(self.project_b)
                    except Exception as e:
                        break
                    sleep(2)

                try:
                    self.jira_admin.create_project(self.project_a,
                                                   self.project_a_name)
                except Exception:
                    # we care only for the project to exist
                    pass
                self.project_a_id = self.jira_admin.project(self.project_a).id
                # except Exception as e:
                #    logging.warning("Got %s" % e)
                # try:
                # assert self.jira_admin.create_project(self.project_b,
                # self.project_b_name) is  True, "Failed to create %s" %
                # self.project_b

                try:
                    self.jira_admin.create_project(self.project_b,
                                                   self.project_b_name)
                except Exception:
                    # we care only for the project to exist
                    pass
                sleep(1)  # keep it here as often JIRA will report the
                # project as missing even after is created
                self.project_b_issue1_obj = self.jira_admin.create_issue(project=self.project_b,
                                                                         summary='issue 1 from %s'
                                                                                 % self.project_b,
                                                                         issuetype=self.CI_JIRA_ISSUE)
                self.project_b_issue1 = self.project_b_issue1_obj.key

                self.project_b_issue2_obj = self.jira_admin.create_issue(project=self.project_b,
                                                                         summary='issue 2 from %s'
                                                                                 % self.project_b,
                                                                         issuetype={'name': self.CI_JIRA_ISSUE})
                self.project_b_issue2 = self.project_b_issue2_obj.key

                self.project_b_issue3_obj = self.jira_admin.create_issue(project=self.project_b,
                                                                         summary='issue 3 from %s'
                                                                                 % self.project_b,
                                                                         issuetype={'name': self.CI_JIRA_ISSUE})
                self.project_b_issue3 = self.project_b_issue3_obj.key

            except Exception as e:
                logging.exception("Basic test setup failed")
                self.initialized = 1
                py.test.exit("FATAL: %s\n%s" % (e, traceback.format_exc()))

            if not hasattr(self, 'jira_normal') or not hasattr(self, 'jira_admin'):
                py.test.exit("FATAL: WTF!?")

            self.initialized = 1

        else:
            # already exist but we need to be sure it was initialized
            counter = 0
            while not self.initialized:
                sleep(1)
                counter += 1
                if counter > 60:
                    logging.fatal("Something is clearly not right with " +
                                  "initialization, killing the tests to prevent a " +
                                  "deadlock.")
                    sys.exit(3)


def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item['key'] == key:
            return seq_item


def find_by_key_value(seq, key):
    for seq_item in seq:
        if seq_item.key == key:
            return seq_item


def find_by_id(seq, id):
    for seq_item in seq:
        if seq_item.id == id:
            return seq_item


def find_by_name(seq, name):
    for seq_item in seq:
        if seq_item['name'] == name:
            return seq_item


@flaky
class UniversalResourceTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.test_manager = JiraTestManager()

    def test_universal_find_existing_resource(self):
        resource = self.jira.find('issue/{0}',
                                  self.test_manager.project_b_issue1)
        issue = self.jira.issue(self.test_manager.project_b_issue1)
        self.assertEqual(resource.self, issue.self)
        self.assertEqual(resource.key, issue.key)

    def test_find_invalid_resource_raises_exception(self):
        with self.assertRaises(JIRAError) as cm:
            self.jira.find('woopsydoodle/{0}', '666')

        ex = cm.exception
        # py26,27,34 gets 404 but on py33 gets 400
        assert ex.status_code in [400, 404]
        self.assertIsNotNone(ex.text)
        self.assertRegex(ex.url, '^https?://.*/rest/api/(2|latest)/woopsydoodle/666$')

    def test_pickling_resource(self):
        resource = self.jira.find('issue/{0}',
                                  self.test_manager.project_b_issue1)

        pickled = pickle.dumps(resource.raw)
        unpickled = pickle.loads(pickled)
        cls = cls_for_resource(unpickled['self'])
        unpickled_instance = cls(self.jira._options, self.jira._session, raw=pickle.loads(pickled))
        self.assertEqual(resource.key, unpickled_instance.key)
        self.assertTrue(resource == unpickled_instance)


@flaky
class ResourceTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_cls_for_resource(self):
        self.assertEqual(cls_for_resource('https://jira.atlassian.com/rest/\
                api/latest/issue/JRA-1330'), Issue)
        self.assertEqual(cls_for_resource('http://localhost:2990/jira/rest/\
                api/latest/project/BULK'), Project)
        self.assertEqual(cls_for_resource('http://imaginary-jira.com/rest/\
                api/latest/project/IMG/role/10002'), Role)
        self.assertEqual(cls_for_resource('http://customized-jira.com/rest/\
                plugin-resource/4.5/json/getMyObject'), Resource)


@flaky
class ApplicationPropertiesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_application_properties(self):
        props = self.jira.application_properties()
        for p in props:
            self.assertIsInstance(p, dict)
            self.assertTrue(set(p.keys()).issuperset(set(['type', 'name', 'value', 'key', 'id'])))

    def test_application_property(self):
        clone_prefix = self.jira.application_properties(
            key='jira.lf.text.headingcolour')
        self.assertEqual(clone_prefix['value'], '#292929')

    @pytest.mark.skipif(_non_parallel, reason="avoid concurrency conflict")
    def test_set_application_property(self):
        prop = 'jira.lf.favicon.hires.url'
        valid_value = '/jira-favicon-hires.png'
        invalid_value = '/Tjira-favicon-hires.png'

        self.jira.set_application_property(prop, invalid_value)
        self.assertEqual(self.jira.application_properties(key=prop)['value'],
                         invalid_value)
        self.jira.set_application_property(prop, valid_value)
        self.assertEqual(self.jira.application_properties(key=prop)['value'],
                         valid_value)

    def test_setting_bad_property_raises(self):
        prop = 'random.nonexistent.property'
        self.assertRaises(JIRAError, self.jira.set_application_property, prop,
                          '666')


@flaky
class AttachmentTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1
        self.attachment = None

    def test_0_attachment_meta(self):
        meta = self.jira.attachment_meta()
        self.assertTrue(meta['enabled'])
        self.assertEqual(meta['uploadLimit'], 10485760)

    @unittest.skip("TBD: investigate failure")
    def test_1_add_remove_attachment(self):
        issue = self.jira.issue(self.issue_1)
        attachment = self.jira.add_attachment(issue,
                                              open(TEST_ATTACH_PATH, 'rb'),
                                              "new test attachment")
        new_attachment = self.jira.attachment(attachment.id)
        msg = "attachment %s of issue %s" % (new_attachment.__dict__, issue)
        self.assertEqual(
            new_attachment.filename, 'new test attachment', msg=msg)
        self.assertEqual(
            new_attachment.size, os.path.getsize(TEST_ATTACH_PATH), msg=msg)
        assert attachment.delete() is None


@flaky
class ComponentTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

    def test_2_create_component(self):
        proj = self.jira.project(self.project_b)
        name = "project-%s-component-%s" % (proj, rndstr())
        component = self.jira.create_component(name,
                                               proj, description='test!!', assigneeType='COMPONENT_LEAD',
                                               isAssigneeTypeValid=False)
        self.assertEqual(component.name, name)
        self.assertEqual(component.description, 'test!!')
        self.assertEqual(component.assigneeType, 'COMPONENT_LEAD')
        self.assertFalse(component.isAssigneeTypeValid)
        component.delete()

    # Components field can't be modified from issue.update
    #    def test_component_count_related_issues(self):
    #        component = self.jira.create_component('PROJECT_B_TEST',self.project_b, description='test!!',
    #                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
    #        issue1 = self.jira.issue(self.issue_1)
    #        issue2 = self.jira.issue(self.issue_2)
    #        (issue1.update ({'components': ['PROJECT_B_TEST']}))
    #        (issue2.update (components = ['PROJECT_B_TEST']))
    #        issue_count = self.jira.component_count_related_issues(component.id)
    #        self.assertEqual(issue_count, 2)
    #        component.delete()

    def test_3_update(self):
        try:
            components = self.jira.project_components(self.project_b)
            for component in components:
                if component.name == 'To be updated':
                    component.delete()
                    break
        except Exception:
            # We ignore errors as this code intends only to prepare for
            # component creation
            raise

        name = 'component-' + rndstr()

        component = self.jira.create_component(name,
                                               self.project_b, description='stand by!',
                                               leadUserName=self.test_manager.CI_JIRA_ADMIN)
        name = 'renamed-' + name
        component.update(name=name, description='It is done.',
                         leadUserName=self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(component.name, name)
        self.assertEqual(component.description, 'It is done.')
        self.assertEqual(component.lead.name, self.test_manager.CI_JIRA_ADMIN)
        component.delete()

    def test_4_delete(self):
        component = self.jira.create_component('To be deleted',
                                               self.project_b, description='not long for this world')
        myid = component.id
        component.delete()
        self.assertRaises(JIRAError, self.jira.component, myid)


@flaky
class CustomFieldOptionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    @not_on_custom_jira_instance
    def test_custom_field_option(self):
        option = self.jira.custom_field_option('10001')
        self.assertEqual(option.value, 'To Do')


@not_on_custom_jira_instance
@flaky
class DashboardTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertEqual(len(dashboards), 3)

    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter='my')
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, '10101')

    def test_dashboards_startat(self):
        dashboards = self.jira.dashboards(startAt=1, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxresults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        dashboard = self.jira.dashboard('10101')
        self.assertEqual(dashboard.id, '10101')
        self.assertEqual(dashboard.name, 'Another test dashboard')


@not_on_custom_jira_instance
@flaky
class FieldsTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_fields(self):
        fields = self.jira.fields()
        self.assertGreater(len(fields), 10)


@flaky
class FilterTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

    def test_filter(self):
        jql = "project = %s and component is not empty" % self.project_b
        name = 'same filter ' + rndstr()
        myfilter = self.jira.create_filter(name=name,
                                           description="just some new test filter", jql=jql,
                                           favourite=False)
        self.assertEqual(myfilter.name, name)
        self.assertEqual(myfilter.owner.name, self.test_manager.CI_JIRA_ADMIN)
        myfilter.delete()

    def test_favourite_filters(self):
        # filters = self.jira.favourite_filters()
        jql = "project = %s and component is not empty" % self.project_b
        name = "filter-to-fav-" + rndstr()
        myfilter = self.jira.create_filter(name=name,
                                           description="just some new test filter", jql=jql,
                                           favourite=True)
        new_filters = self.jira.favourite_filters()

        assert name in [f.name for f in new_filters]
        myfilter.delete()


@not_on_custom_jira_instance
@flaky
class GroupsTest(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = self.test_manager.jira_admin

    def test_groups(self):
        groups = self.jira.groups()
        self.assertGreater(len(groups), 0)

    def test_groups_for_users(self):
        groups = self.jira.groups('jira-users')
        self.assertGreater(len(groups), 0)


@flaky
class IssueTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.jira_normal = JiraTestManager().jira_normal
        self.project_b = self.test_manager.project_b
        self.project_a = self.test_manager.project_a
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

    def test_issue(self):
        issue = self.jira.issue(self.issue_1)
        self.assertEqual(issue.key, self.issue_1)
        self.assertEqual(issue.fields.summary,
                         'issue 1 from %s' % self.project_b)

    @unittest.skip("disabled as it seems to be ignored by jira, returning all")
    def test_issue_field_limiting(self):
        issue = self.jira.issue(self.issue_2, fields='summary,comment')
        self.assertEqual(issue.fields.summary,
                         'issue 2 from %s' % self.project_b)
        comment1 = self.jira.add_comment(issue, 'First comment')
        comment2 = self.jira.add_comment(issue, 'Second comment')
        comment3 = self.jira.add_comment(issue, 'Third comment')
        self.jira.issue(self.issue_2, fields='summary,comment')
        logging.warning(issue.raw['fields'])
        self.assertFalse(hasattr(issue.fields, 'reporter'))
        self.assertFalse(hasattr(issue.fields, 'progress'))
        comment1.delete()
        comment2.delete()
        comment3.delete()

    def test_issue_equal(self):
        issue1 = self.jira.issue(self.issue_1)
        issue2 = self.jira.issue(self.issue_2)
        issues = self.jira.search_issues('key=%s' % self.issue_1)
        self.assertTrue(issue1 == issues[0])
        self.assertFalse(issue2 == issues[0])

    def test_issue_expandos(self):
        issue = self.jira.issue(self.issue_1, expand='editmeta,schema')
        self.assertTrue(hasattr(issue, 'editmeta'))
        self.assertTrue(hasattr(issue, 'schema'))
        # testing for changelog is not reliable because it may exist or not based on test order
        # self.assertFalse(hasattr(issue, 'changelog'))

    @not_on_custom_jira_instance
    def test_create_issue_with_fieldargs(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue created', description='blahery',
                                       issuetype={'name': 'Bug'})  # customfield_10022='XSS'
        self.assertEqual(issue.fields.summary, 'Test issue created')
        self.assertEqual(issue.fields.description, 'blahery')
        self.assertEqual(issue.fields.issuetype.name, 'Bug')
        self.assertEqual(issue.fields.project.key, self.project_b)
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        issue.delete()

    @not_on_custom_jira_instance
    def test_create_issue_with_fielddict(self):
        fields = {
            'project': {
                'key': self.project_b},
            'summary': 'Issue created from field dict',
            'description': "Some new issue for test",
            'issuetype': {
                'name': 'Bug'},
            # 'customfield_10022': 'XSS',
            'priority': {
                'name': 'Major'}}
        issue = self.jira.create_issue(fields=fields)
        self.assertEqual(issue.fields.summary,
                         'Issue created from field dict')
        self.assertEqual(issue.fields.description, "Some new issue for test")
        self.assertEqual(issue.fields.issuetype.name, 'Bug')
        self.assertEqual(issue.fields.project.key, self.project_b)
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.priority.name, 'Major')
        issue.delete()

    @not_on_custom_jira_instance
    def test_create_issue_without_prefetch(self):
        issue = self.jira.create_issue(prefetch=False,
                                       project=self.project_b,
                                       summary='Test issue created',
                                       description='blahery', issuetype={'name': 'Bug'}
                                       )  # customfield_10022='XSS'

        assert hasattr(issue, 'self')
        assert hasattr(issue, 'raw')
        assert 'fields' not in issue.raw
        issue.delete()

    @not_on_custom_jira_instance
    def test_create_issues(self):
        field_list = [{
            'project': {
                'key': self.project_b},
            'summary': 'Issue created via bulk create #1',
            'description': "Some new issue for test",
            'issuetype': {
                'name': 'Bug'},
            # 'customfield_10022': 'XSS',
            'priority': {
                'name': 'Major'}},
            {
            'project': {
                'key': self.project_a},
            'issuetype': {
                'name': 'Bug'},
            'summary': 'Issue created via bulk create #2',
            'description': "Another new issue for bulk test",
            'priority': {
                'name': 'Major'}}]
        issues = self.jira.create_issues(field_list=field_list)
        self.assertEqual(issues[0]['issue'].fields.summary,
                         'Issue created via bulk create #1')
        self.assertEqual(issues[0]['issue'].fields.description,
                         "Some new issue for test")
        self.assertEqual(issues[0]['issue'].fields.issuetype.name, 'Bug')
        self.assertEqual(issues[0]['issue'].fields.project.key, self.project_b)
        self.assertEqual(issues[0]['issue'].fields.priority.name, 'Major')
        self.assertEqual(issues[1]['issue'].fields.summary,
                         'Issue created via bulk create #2')
        self.assertEqual(issues[1]['issue'].fields.description,
                         "Another new issue for bulk test")
        self.assertEqual(issues[1]['issue'].fields.issuetype.name, 'Bug')
        self.assertEqual(issues[1]['issue'].fields.project.key, self.project_a)
        self.assertEqual(issues[1]['issue'].fields.priority.name, 'Major')
        for issue in issues:
            issue['issue'].delete()

    @not_on_custom_jira_instance
    def test_create_issues_one_failure(self):
        field_list = [{
            'project': {
                'key': self.project_b},
            'summary': 'Issue created via bulk create #1',
            'description': "Some new issue for test",
            'issuetype': {
                'name': 'Bug'},
            # 'customfield_10022': 'XSS',
            'priority': {
                'name': 'Major'}},
            {'project': {
                'key': self.project_a},
                'issuetype': {
                    'name': 'InvalidIssueType'},
                'summary': 'This issue will not succeed',
                'description': "Should not be seen.",
                'priority': {
                'name': 'Blah'}},
            {'project': {
                'key': self.project_a},
                'issuetype': {
                    'name': 'Bug'},
                'summary': 'However, this one will.',
                'description': "Should be seen.",
                'priority': {
                    'name': 'Major'}}]
        issues = self.jira.create_issues(field_list=field_list)
        self.assertEqual(issues[0]['issue'].fields.summary,
                         'Issue created via bulk create #1')
        self.assertEqual(issues[0]['issue'].fields.description,
                         "Some new issue for test")
        self.assertEqual(issues[0]['issue'].fields.issuetype.name, 'Bug')
        self.assertEqual(issues[0]['issue'].fields.project.key, self.project_b)
        self.assertEqual(issues[0]['issue'].fields.priority.name, 'Major')
        self.assertEqual(issues[0]['error'], None)
        self.assertEqual(issues[1]['issue'], None)
        self.assertEqual(issues[1]['error'], {'issuetype': 'issue type is required'})
        self.assertEqual(issues[1]['input_fields'], field_list[1])
        self.assertEqual(issues[2]['issue'].fields.summary,
                         'However, this one will.')
        self.assertEqual(issues[2]['issue'].fields.description,
                         "Should be seen.")
        self.assertEqual(issues[2]['issue'].fields.issuetype.name, 'Bug')
        self.assertEqual(issues[2]['issue'].fields.project.key, self.project_a)
        self.assertEqual(issues[2]['issue'].fields.priority.name, 'Major')
        self.assertEqual(issues[2]['error'], None)
        self.assertEqual(len(issues), 3)
        for issue in issues:
            if issue['issue'] is not None:
                issue['issue'].delete()

    @not_on_custom_jira_instance
    def test_create_issues_without_prefetch(self):
        field_list = [dict(project=self.project_b,
                           summary='Test issue created',
                           description='blahery',
                           issuetype={'name': 'Bug'}),
                      dict(project=self.project_a,
                           summary='Test issue #2',
                           description='fooery',
                           issuetype={'name': 'Bug'})]
        issues = self.jira.create_issues(field_list, prefetch=False)

        assert hasattr(issues[0]['issue'], 'self')
        assert hasattr(issues[0]['issue'], 'raw')
        assert hasattr(issues[1]['issue'], 'self')
        assert hasattr(issues[1]['issue'], 'raw')
        assert 'fields' not in issues[0]['issue'].raw
        assert 'fields' not in issues[1]['issue'].raw
        for issue in issues:
            issue['issue'].delete()

    @not_on_custom_jira_instance
    def test_update_with_fieldargs(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue for updating',
                                       description='Will be updated shortly',
                                       issuetype={'name': 'Bug'})
        # customfield_10022='XSS')
        issue.update(summary='Updated summary', description='Now updated',
                     issuetype={'name': 'Improvement'})
        self.assertEqual(issue.fields.summary, 'Updated summary')
        self.assertEqual(issue.fields.description, 'Now updated')
        self.assertEqual(issue.fields.issuetype.name, 'Improvement')
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.project.key, self.project_b)
        issue.delete()

    @not_on_custom_jira_instance
    def test_update_with_fielddict(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue for updating', description='Will be updated shortly',
                                       issuetype={'name': 'Bug'})
        fields = {
            'summary': 'Issue is updated',
            'description': "it sure is",
            'issuetype': {
                'name': 'Improvement'},
            # 'customfield_10022': 'DOC',
            'priority': {
                'name': 'Major'}}
        issue.update(fields=fields)
        self.assertEqual(issue.fields.summary, 'Issue is updated')
        self.assertEqual(issue.fields.description, 'it sure is')
        self.assertEqual(issue.fields.issuetype.name, 'Improvement')
        # self.assertEqual(issue.fields.customfield_10022, 'DOC')
        self.assertEqual(issue.fields.priority.name, 'Major')
        issue.delete()

    def test_update_with_label(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue for updating labels', description='Label testing',
                                       issuetype=self.test_manager.CI_JIRA_ISSUE)

        labelarray = ['testLabel']
        fields = {
            'labels': labelarray}

        issue.update(fields=fields)
        self.assertEqual(issue.fields.labels, ['testLabel'])

    def test_update_with_bad_label(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue for updating labels', description='Label testing',
                                       issuetype=self.test_manager.CI_JIRA_ISSUE)

        issue.fields.labels.append('this should not work')

        fields = {
            'labels': issue.fields.labels}

        self.assertRaises(JIRAError, issue.update, fields=fields)

    @not_on_custom_jira_instance
    def test_update_with_notify_false(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue for updating',
                                       description='Will be updated shortly',
                                       issuetype={'name': 'Bug'})
        issue.update(notify=False, description='Now updated, but silently')
        self.assertEqual(issue.fields.description, 'Now updated, but silently')
        issue.delete()

    def test_delete(self):
        issue = self.jira.create_issue(project=self.project_b,
                                       summary='Test issue created',
                                       description='Not long for this world',
                                       issuetype=self.test_manager.CI_JIRA_ISSUE)
        key = issue.key
        issue.delete()
        self.assertRaises(JIRAError, self.jira.issue, key)

    @not_on_custom_jira_instance
    def test_createmeta(self):
        meta = self.jira.createmeta()
        ztravisdeb_proj = find_by_key(meta['projects'], self.project_b)
        # we assume that this project should allow at least one issue type
        self.assertGreaterEqual(len(ztravisdeb_proj['issuetypes']), 1)

    @not_on_custom_jira_instance
    def test_createmeta_filter_by_projectkey_and_name(self):
        meta = self.jira.createmeta(projectKeys=self.project_b,
                                    issuetypeNames='Bug')
        self.assertEqual(len(meta['projects']), 1)
        self.assertEqual(len(meta['projects'][0]['issuetypes']), 1)

    @not_on_custom_jira_instance
    def test_createmeta_filter_by_projectkeys_and_name(self):
        meta = self.jira.createmeta(projectKeys=(self.project_a,
                                                 self.project_b), issuetypeNames='Improvement')
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertEqual(len(project['issuetypes']), 1)

    @not_on_custom_jira_instance
    def test_createmeta_filter_by_id(self):
        projects = self.jira.projects()
        proja = find_by_key_value(projects, self.project_a)
        projb = find_by_key_value(projects, self.project_b)
        meta = self.jira.createmeta(projectIds=(proja.id, projb.id),
                                    issuetypeIds=('3', '4', '5'))
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertEqual(len(project['issuetypes']), 3)

    def test_createmeta_expando(self):
        # limit to SCR project so the call returns promptly
        meta = self.jira.createmeta(projectKeys=self.project_b,
                                    expand='projects.issuetypes.fields')
        self.assertTrue('fields' in meta['projects'][0]['issuetypes'][0])

    def test_assign_issue(self):
        self.assertTrue(self.jira.assign_issue(self.issue_1, self.test_manager.CI_JIRA_ADMIN))
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee.name,
                         self.test_manager.CI_JIRA_ADMIN)

    def test_assign_issue_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        x = self.jira.assign_issue(issue, self.test_manager.CI_JIRA_ADMIN)
        self.assertTrue(x)
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee.name,
                         self.test_manager.CI_JIRA_ADMIN)

    def test_assign_to_bad_issue_raises(self):
        self.assertRaises(JIRAError, self.jira.assign_issue, 'NOPE-1',
                          'notauser')

    def test_comments(self):
        for issue in [self.issue_1, self.jira.issue(self.issue_2)]:
            self.jira.issue(issue)
            comment1 = self.jira.add_comment(issue, 'First comment')
            comment2 = self.jira.add_comment(issue, 'Second comment')
            comments = self.jira.comments(issue)
            assert comments[0].body == 'First comment'
            assert comments[1].body == 'Second comment'
            comment1.delete()
            comment2.delete()
            comments = self.jira.comments(issue)
            assert len(comments) == 0

    def test_add_comment(self):
        comment = self.jira.add_comment(self.issue_3, 'a test comment!',
                                        visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'a test comment!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_add_comment_with_issue_obj(self):
        issue = self.jira.issue(self.issue_3)
        comment = self.jira.add_comment(issue, 'a new test comment!',
                                        visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'a new test comment!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_update_comment(self):
        comment = self.jira.add_comment(self.issue_3, 'updating soon!')
        comment.update(body='updated!')
        self.assertEqual(comment.body, 'updated!')
        # self.assertEqual(comment.visibility.type, 'role')
        # self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_editmeta(self):
        for i in (self.issue_1, self.issue_2):
            meta = self.jira.editmeta(i)
            self.assertTrue('assignee' in meta['fields'])
            self.assertTrue('attachment' in meta['fields'])
            self.assertTrue('comment' in meta['fields'])
            self.assertTrue('components' in meta['fields'])
            self.assertTrue('description' in meta['fields'])
            self.assertTrue('duedate' in meta['fields'])
            self.assertTrue('environment' in meta['fields'])
            self.assertTrue('fixVersions' in meta['fields'])
            self.assertTrue('issuelinks' in meta['fields'])
            self.assertTrue('issuetype' in meta['fields'])
            self.assertTrue('labels' in meta['fields'])
            self.assertTrue('versions' in meta['fields'])

    # Nothing from remote link works
    #    def test_remote_links(self):
    #        self.jira.add_remote_link ('ZTRAVISDEB-3', globalId='python-test:story.of.horse.riding',
    #        links = self.jira.remote_links('QA-44')
    #        self.assertEqual(len(links), 1)
    #        links = self.jira.remote_links('BULK-1')
    #        self.assertEqual(len(links), 0)
    #
    #    @unittest.skip("temporary disabled")
    #    def test_remote_links_with_issue_obj(self):
    #        issue = self.jira.issue('QA-44')
    #        links = self.jira.remote_links(issue)
    #        self.assertEqual(len(links), 1)
    #        issue = self.jira.issue('BULK-1')
    #        links = self.jira.remote_links(issue)
    #        self.assertEqual(len(links), 0)
    #
    #    @unittest.skip("temporary disabled")
    #    def test_remote_link(self):
    #        link = self.jira.remote_link('QA-44', '10000')
    #        self.assertEqual(link.id, 10000)
    #        self.assertTrue(hasattr(link, 'globalId'))
    #        self.assertTrue(hasattr(link, 'relationship'))
    #
    #    @unittest.skip("temporary disabled")
    #    def test_remote_link_with_issue_obj(self):
    #        issue = self.jira.issue('QA-44')
    #        link = self.jira.remote_link(issue, '10000')
    #        self.assertEqual(link.id, 10000)
    #        self.assertTrue(hasattr(link, 'globalId'))
    #        self.assertTrue(hasattr(link, 'relationship'))
    #
    #    @unittest.skip("temporary disabled")
    #    def test_add_remote_link(self):
    #        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
    #                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
    #                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
    # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
    #        link = self.jira.remote_link('BULK-3', link.id)
    #        self.assertEqual(link.application.name, 'far too silly')
    #        self.assertEqual(link.application.type, 'sketch')
    #        self.assertEqual(link.object.url, 'http://google.com')
    #        self.assertEqual(link.object.title, 'googlicious!')
    #        self.assertEqual(link.relationship, 'mousebending')
    #        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
    #
    #    @unittest.skip("temporary disabled")
    #    def test_add_remote_link_with_issue_obj(self):
    #        issue = self.jira.issue('BULK-3')
    #        link = self.jira.add_remote_link(issue, globalId='python-test:story.of.horse.riding',
    #                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
    #                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
    # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
    #        link = self.jira.remote_link(issue, link.id)
    #        self.assertEqual(link.application.name, 'far too silly')
    #        self.assertEqual(link.application.type, 'sketch')
    #        self.assertEqual(link.object.url, 'http://google.com')
    #        self.assertEqual(link.object.title, 'googlicious!')
    #        self.assertEqual(link.relationship, 'mousebending')
    #        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
    #
    #    @unittest.skip("temporary disabled")
    #    def test_update_remote_link(self):
    #        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
    #                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
    #                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
    # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
    #        link = self.jira.remote_link('BULK-3', link.id)
    #        link.update(object={'url': 'http://yahoo.com', 'title': 'yahooery'}, globalId='python-test:updated.id',
    #                    relationship='cheesing')
    #        self.assertEqual(link.globalId, 'python-test:updated.id')
    #        self.assertEqual(link.relationship, 'cheesing')
    #        self.assertEqual(link.object.url, 'http://yahoo.com')
    #        self.assertEqual(link.object.title, 'yahooery')
    #        link.delete()
    #
    #    @unittest.skip("temporary disabled")
    #    def test_delete_remove_link(self):
    #        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
    #                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
    #                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
    #        _id = link.id
    #        link.delete()
    #        self.assertRaises(JIRAError, self.jira.remote_link, 'BULK-3', _id)

    def test_transitioning(self):
        # we check with both issue-as-string or issue-as-object
        transitions = []
        for issue in [self.issue_2, self.jira.issue(self.issue_2)]:
            transitions = self.jira.transitions(issue)
            self.assertTrue(transitions)
            self.assertTrue('id' in transitions[0])
            self.assertTrue('name' in transitions[0])

        self.assertTrue(transitions, msg="Expecting at least one transition")
        # we test getting a single transition
        transition = self.jira.transitions(self.issue_2, transitions[0]['id'])[0]
        self.assertDictEqual(transition, transitions[0])

        # we test the expand of fields
        transition = self.jira.transitions(self.issue_2, transitions[0]['id'],
                                           expand='transitions.fields')[0]
        self.assertTrue('fields' in transition)

        # Testing of transition with field assignment is disabled now because default workflows do not have it.

        # self.jira.transition_issue(issue, transitions[0]['id'], assignee={'name': self.test_manager.CI_JIRA_ADMIN})
        # issue = self.jira.issue(issue.key)
        # self.assertEqual(issue.fields.assignee.name, self.test_manager.CI_JIRA_ADMIN)
        #
        # fields = {
        #     'assignee': {
        #         'name': self.test_manager.CI_JIRA_USER
        #     }
        # }
        # transitions = self.jira.transitions(issue.key)
        # self.assertTrue(transitions)  # any issue should have at least one transition available to it
        # transition_id = transitions[0]['id']
        #
        # self.jira.transition_issue(issue.key, transition_id, fields=fields)
        # issue = self.jira.issue(issue.key)
        # self.assertEqual(issue.fields.assignee.name, self.test_manager.CI_JIRA_USER)
        # self.assertEqual(issue.fields.status.id, transition_id)

    def test_votes(self):
        self.jira_normal.remove_vote(self.issue_1)
        # not checking the result on this
        votes = self.jira.votes(self.issue_1)
        self.assertEqual(votes.votes, 0)

        self.jira_normal.add_vote(self.issue_1)
        new_votes = self.jira.votes(self.issue_1)
        assert votes.votes + 1 == new_votes.votes

        self.jira_normal.remove_vote(self.issue_1)
        new_votes = self.jira.votes(self.issue_1)
        assert votes.votes == new_votes.votes

    def test_votes_with_issue_obj(self):
        issue = self.jira_normal.issue(self.issue_1)
        self.jira_normal.remove_vote(issue)
        # not checking the result on this
        votes = self.jira.votes(issue)
        self.assertEqual(votes.votes, 0)

        self.jira_normal.add_vote(issue)
        new_votes = self.jira.votes(issue)
        assert votes.votes + 1 == new_votes.votes

        self.jira_normal.remove_vote(issue)
        new_votes = self.jira.votes(issue)
        assert votes.votes == new_votes.votes

    def test_add_remove_watcher(self):

        # removing it in case it exists, so we know its state
        self.jira.remove_watcher(self.issue_1, self.test_manager.CI_JIRA_USER)
        init_watchers = self.jira.watchers(self.issue_1).watchCount

        # adding a new watcher
        self.jira.add_watcher(self.issue_1, self.test_manager.CI_JIRA_USER)
        self.assertEqual(self.jira.watchers(self.issue_1).watchCount,
                         init_watchers + 1)

        # now we verify that remove does indeed remove watchers
        self.jira.remove_watcher(self.issue_1, self.test_manager.CI_JIRA_USER)
        new_watchers = self.jira.watchers(self.issue_1).watchCount
        self.assertEqual(init_watchers, new_watchers)

    @not_on_custom_jira_instance
    def test_agile(self):
        uniq = rndstr()
        board_name = 'board-' + uniq
        sprint_name = 'sprint-' + uniq

        b = self.jira.create_board(board_name, self.project_a)
        assert isinstance(b.id, integer_types)

        s = self.jira.create_sprint(sprint_name, b.id)
        assert isinstance(s.id, integer_types)
        assert s.name == sprint_name
        assert s.state == 'FUTURE'

        self.jira.add_issues_to_sprint(s.id, [self.issue_1])

        sprint_field_name = "Sprint"
        sprint_field_id = [f['schema']['customId'] for f in self.jira.fields()
                           if f['name'] == sprint_field_name][0]
        sprint_customfield = "customfield_" + str(sprint_field_id)

        updated_issue_1 = self.jira.issue(self.issue_1)
        serialised_sprint = getattr(updated_issue_1.fields, sprint_customfield)[0]

        # Too hard to serialise the sprint object. Performing simple regex match instead.
        assert re.search('\[id=' + str(s.id) + ',', serialised_sprint)

        # self.jira.add_issues_to_sprint(s.id, self.issue_2)

        # self.jira.rank(self.issue_2, self.issue_1)

        sleep(2)  # avoid https://travis-ci.org/pycontribs/jira/jobs/176561534#L516
        s.delete()

        sleep(2)
        b.delete()
        # self.jira.delete_board(b.id)

    def test_worklogs(self):
        worklog = self.jira.add_worklog(self.issue_1, '2h')
        worklogs = self.jira.worklogs(self.issue_1)
        self.assertEqual(len(worklogs), 1)
        worklog.delete()

    def test_worklogs_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        worklog = self.jira.add_worklog(issue, '2h')
        worklogs = self.jira.worklogs(issue)
        self.assertEqual(len(worklogs), 1)
        worklog.delete()

    def test_worklog(self):
        worklog = self.jira.add_worklog(self.issue_1, '1d 2h')
        new_worklog = self.jira.worklog(self.issue_1, str(worklog))
        self.assertEqual(new_worklog.author.name, self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(new_worklog.timeSpent, '1d 2h')
        worklog.delete()

    def test_worklog_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        worklog = self.jira.add_worklog(issue, '1d 2h')
        new_worklog = self.jira.worklog(issue, str(worklog))
        self.assertEqual(new_worklog.author.name, self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(new_worklog.timeSpent, '1d 2h')
        worklog.delete()

    def test_add_worklog(self):
        worklog_count = len(self.jira.worklogs(self.issue_2))
        worklog = self.jira.add_worklog(self.issue_2, '2h')
        self.assertIsNotNone(worklog)
        self.assertEqual(len(self.jira.worklogs(self.issue_2)), worklog_count + 1)
        worklog.delete()

    def test_add_worklog_with_issue_obj(self):
        issue = self.jira.issue(self.issue_2)
        worklog_count = len(self.jira.worklogs(issue))
        worklog = self.jira.add_worklog(issue, '2h')
        self.assertIsNotNone(worklog)
        self.assertEqual(len(self.jira.worklogs(issue)), worklog_count + 1)
        worklog.delete()

    def test_update_and_delete_worklog(self):
        worklog = self.jira.add_worklog(self.issue_3, '3h')
        issue = self.jira.issue(self.issue_3, fields='worklog,timetracking')
        worklog.update(comment='Updated!', timeSpent='2h')
        self.assertEqual(worklog.comment, 'Updated!')
        # rem_estimate = issue.fields.timetracking.remainingEstimate
        self.assertEqual(worklog.timeSpent, '2h')
        issue = self.jira.issue(self.issue_3, fields='worklog,timetracking')
        self.assertEqual(issue.fields.timetracking.remainingEstimate, "1h")
        worklog.delete()
        issue = self.jira.issue(self.issue_3, fields='worklog,timetracking')
        self.assertEqual(issue.fields.timetracking.remainingEstimate, "3h")


@flaky
class IssueLinkTests(unittest.TestCase):

    def setUp(self):
        self.manager = JiraTestManager()
        self.link_types = self.manager.jira_admin.issue_link_types()

    def test_issue_link(self):
        self.link = self.manager.jira_admin.issue_link_type(self.link_types[0].id)
        link = self.link  # Duplicate outward
        self.assertEqual(link.id, self.link_types[0].id)

    def test_create_issue_link(self):
        self.manager.jira_admin.create_issue_link(self.link_types[0].outward,
                                                  JiraTestManager().project_b_issue1,
                                                  JiraTestManager().project_b_issue2)

    def test_create_issue_link_with_issue_objs(self):
        inwardissue = self.manager.jira_admin.issue(
            JiraTestManager().project_b_issue1)
        self.assertIsNotNone(inwardissue)
        outwardissue = self.manager.jira_admin.issue(
            JiraTestManager().project_b_issue2)
        self.assertIsNotNone(outwardissue)
        self.manager.jira_admin.create_issue_link(self.link_types[0].outward,
                                                  inwardissue, outwardissue)

        # @unittest.skip("Creating an issue link doesn't return its ID, so can't easily test delete")
        # def test_delete_issue_link(self):
        #    pass

    def test_issue_link_type(self):
        link_type = self.manager.jira_admin.issue_link_type(self.link_types[0].id)
        self.assertEqual(link_type.id, self.link_types[0].id)
        self.assertEqual(link_type.name, self.link_types[0].name)


@flaky
class MyPermissionsTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_normal
        self.issue_1 = self.test_manager.project_b_issue1

    def test_my_permissions(self):
        perms = self.jira.my_permissions()
        self.assertGreaterEqual(len(perms['permissions']), 40)

    def test_my_permissions_by_project(self):
        perms = self.jira.my_permissions(projectKey=self.test_manager.project_a)
        self.assertGreaterEqual(len(perms['permissions']), 10)
        perms = self.jira.my_permissions(projectId=self.test_manager.project_a_id)
        self.assertGreaterEqual(len(perms['permissions']), 10)

    @unittest.skip("broken")
    def test_my_permissions_by_issue(self):
        perms = self.jira.my_permissions(issueKey='ZTRAVISDEB-7')
        self.assertGreaterEqual(len(perms['permissions']), 10)
        perms = self.jira.my_permissions(issueId='11021')
        self.assertGreaterEqual(len(perms['permissions']), 10)


@flaky
class PrioritiesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_priorities(self):
        priorities = self.jira.priorities()
        self.assertEqual(len(priorities), 5)

    @not_on_custom_jira_instance
    def test_priority(self):
        priority = self.jira.priority('2')
        self.assertEqual(priority.id, '2')
        self.assertEqual(priority.name, 'Critical')


@flaky
class ProjectTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.project_b = JiraTestManager().project_b
        self.test_manager = JiraTestManager()

    def test_projects(self):
        projects = self.jira.projects()
        self.assertGreaterEqual(len(projects), 2)

    def test_project(self):
        project = self.jira.project(self.project_b)
        self.assertEqual(project.key, self.project_b)

    # I have no idea what avatars['custom'] is and I get different results every time
    #    def test_project_avatars(self):
    #        avatars = self.jira.project_avatars(self.project_b)
    #        self.assertEqual(len(avatars['custom']), 3)
    #        self.assertEqual(len(avatars['system']), 16)
    #
    #    def test_project_avatars_with_project_obj(self):
    #        project = self.jira.project(self.project_b)
    #        avatars = self.jira.project_avatars(project)
    #        self.assertEqual(len(avatars['custom']), 3)
    #        self.assertEqual(len(avatars['system']), 16)

    #    def test_create_project_avatar(self):
    # Tests the end-to-end project avatar creation process: upload as temporary, confirm after cropping,
    # and selection.
    #        project = self.jira.project(self.project_b)
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read())
    #        self.assertIn('cropperOffsetX', props)
    #        self.assertIn('cropperOffsetY', props)
    #        self.assertIn('cropperWidth', props)
    #        self.assertTrue(props['needsCropping'])
    #
    #        props['needsCropping'] = False
    #        avatar_props = self.jira.confirm_project_avatar(project, props)
    #        self.assertIn('id', avatar_props)
    #
    #        self.jira.set_project_avatar(self.project_b, avatar_props['id'])
    #
    #    def test_delete_project_avatar(self):
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(self.project_b, filename, size, icon.read(), auto_confirm=True)
    #        self.jira.delete_project_avatar(self.project_b, props['id'])
    #
    #    def test_delete_project_avatar_with_project_obj(self):
    #        project = self.jira.project(self.project_b)
    #        size = os.path.getsize(TEST_ICON_PATH)
    #        filename = os.path.basename(TEST_ICON_PATH)
    #        with open(TEST_ICON_PATH, "rb") as icon:
    #            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read(), auto_confirm=True)
    #        self.jira.delete_project_avatar(project, props['id'])

    # @pytest.mark.xfail(reason="Jira may return 500")
    # def test_set_project_avatar(self):
    #     def find_selected_avatar(avatars):
    #         for avatar in avatars['system']:
    #             if avatar['isSelected']:
    #                 return avatar
    #         else:
    #             raise Exception
    #
    #     self.jira.set_project_avatar(self.project_b, '10001')
    #     avatars = self.jira.project_avatars(self.project_b)
    #     self.assertEqual(find_selected_avatar(avatars)['id'], '10001')
    #
    #     project = self.jira.project(self.project_b)
    #     self.jira.set_project_avatar(project, '10208')
    #     avatars = self.jira.project_avatars(project)
    #     self.assertEqual(find_selected_avatar(avatars)['id'], '10208')

    def test_project_components(self):
        proj = self.jira.project(self.project_b)
        name = "component-%s from project %s" % (proj, rndstr())
        component = self.jira.create_component(name,
                                               proj, description='test!!', assigneeType='COMPONENT_LEAD',
                                               isAssigneeTypeValid=False)
        components = self.jira.project_components(self.project_b)
        self.assertGreaterEqual(len(components), 1)
        sample = find_by_id(components, component.id)
        self.assertEqual(sample.id, component.id)
        self.assertEqual(sample.name, name)
        component.delete()

    def test_project_versions(self):
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name,
                                           self.project_b, "will be deleted soon")
        versions = self.jira.project_versions(self.project_b)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, name)

        i = self.jira.issue(JiraTestManager().project_b_issue1)
        i.update(fields={
            'versions': [{'id': version.id}],
            'fixVersions': [{'id': version.id}]})
        version.delete()

    def test_project_versions_with_project_obj(self):
        name = "version-%s" % rndstr()
        version = self.jira.create_version(name,
                                           self.project_b, "will be deleted soon")
        project = self.jira.project(self.project_b)
        versions = self.jira.project_versions(project)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, name)
        version.delete()

    @unittest.skip("temporary disabled because roles() return a dictionary of role_name:role_url and we have no call to convert it to proper Role()")
    def test_project_roles(self):
        project = self.jira.project(self.project_b)
        role_name = 'Developers'
        dev = None
        for roles in [self.jira.project_roles(self.project_b), self.jira.project_roles(project)]:
            self.assertGreaterEqual(len(roles), 5)
            self.assertIn('Users', roles)
            self.assertIn(role_name, roles)
            dev = roles[role_name]
        self.assertTrue(dev)
        role = self.jira.project_role(self.project_b, dev.id)
        self.assertEqual(role.id, dev.id)
        self.assertEqual(role.name, dev.name)
        user = self.test_manager.jira_admin
        self.assertNotIn(user, role.actors)
        role.update(users=user, groups=['jira-developers', 'jira-users'])
        role = self.jira.project_role(self.project_b, dev.id)
        self.assertIn(user, role.actors)


@not_on_custom_jira_instance
@flaky
class ResolutionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_resolutions(self):
        resolutions = self.jira.resolutions()
        self.assertGreaterEqual(len(resolutions), 1)

    def test_resolution(self):
        resolution = self.jira.resolution('2')
        self.assertEqual(resolution.id, '2')
        self.assertEqual(resolution.name, 'Won\'t Fix')


@flaky
class SearchTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.project_b = JiraTestManager().project_b
        self.test_manager = JiraTestManager()
        self.issue = self.test_manager.project_b_issue1

    def test_search_issues(self):
        issues = self.jira.search_issues('project=%s' % self.project_b)
        self.assertLessEqual(len(issues), 50)  # default maxResults
        for issue in issues:
            self.assertTrue(issue.key.startswith(self.project_b))

    def test_search_issues_maxresults(self):
        issues = self.jira.search_issues('project=%s' % self.project_b,
                                         maxResults=10)
        self.assertLessEqual(len(issues), 10)

    def test_search_issues_startat(self):
        issues = self.jira.search_issues('project=%s' % self.project_b,
                                         startAt=2, maxResults=10)
        self.assertGreaterEqual(len(issues), 1)
        # we know that project_b should have at least 3 issues

    def test_search_issues_field_limiting(self):
        issues = self.jira.search_issues('key=%s' % self.issue,
                                         fields='summary,comment')
        self.assertTrue(hasattr(issues[0].fields, 'summary'))
        self.assertTrue(hasattr(issues[0].fields, 'comment'))
        self.assertFalse(hasattr(issues[0].fields, 'reporter'))
        self.assertFalse(hasattr(issues[0].fields, 'progress'))

    def test_search_issues_expandos(self):
        issues = self.jira.search_issues('key=%s' % self.issue,
                                         expand='changelog')
        # self.assertTrue(hasattr(issues[0], 'names'))
        self.assertEqual(len(issues), 1)
        self.assertFalse(hasattr(issues[0], 'editmeta'))
        self.assertTrue(hasattr(issues[0], 'changelog'))
        self.assertEqual(issues[0].key, self.issue)


@unittest.skip("Skipped due to https://jira.atlassian.com/browse/JRA-59619")
@flaky
class SecurityLevelTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_security_level(self):
        # This is hardcoded due to Atlassian bug: https://jira.atlassian.com/browse/JRA-59619
        sec_level = self.jira.security_level('10000')
        self.assertEqual(sec_level.id, '10000')


@flaky
class ServerInfoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_server_info(self):
        server_info = self.jira.server_info()
        self.assertIn('baseUrl', server_info)
        self.assertIn('version', server_info)


@flaky
class StatusTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_statuses(self):
        found = False
        statuses = self.jira.statuses()
        for status in statuses:
            if status.id == '10001' and status.name == 'Done':
                found = True
                break
        self.assertTrue(found, "Status Open with id=1 not found. [%s]" % statuses)
        self.assertGreater(len(statuses), 0)

    @flaky
    def test_status(self):
        status = self.jira.status('10001')
        self.assertEqual(status.id, '10001')
        self.assertEqual(status.name, 'Done')


@flaky
class UserTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.project_a = JiraTestManager().project_a
        self.project_b = JiraTestManager().project_b
        self.test_manager = JiraTestManager()
        self.issue = self.test_manager.project_b_issue3

    def test_user(self):
        user = self.jira.user(self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(user.name, self.test_manager.CI_JIRA_ADMIN)
        self.assertRegex(user.emailAddress, '.*@example.com')

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_projects(self):
        users = self.jira.search_assignable_users_for_projects(self.test_manager.CI_JIRA_ADMIN,
                                                               '%s,%s' % (self.project_a, self.project_b))
        self.assertGreaterEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_projects_maxresults(self):
        users = self.jira.search_assignable_users_for_projects(self.test_manager.CI_JIRA_ADMIN,
                                                               '%s,%s' % (self.project_a, self.project_b), maxResults=1)
        self.assertLessEqual(len(users), 1)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_projects_startat(self):
        users = self.jira.search_assignable_users_for_projects(self.test_manager.CI_JIRA_ADMIN,
                                                               '%s,%s' % (self.project_a, self.project_b), startAt=1)
        self.assertGreaterEqual(len(users), 0)

    @not_on_custom_jira_instance
    def test_search_assignable_users_for_issues_by_project(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_ADMIN,
                                                             project=self.project_b)
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_issues_by_project_maxresults(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_USER,
                                                             project=self.project_b, maxResults=1)
        self.assertLessEqual(len(users), 1)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_issues_by_project_startat(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_USER,
                                                             project=self.project_a, startAt=1)
        self.assertGreaterEqual(len(users), 0)

    @not_on_custom_jira_instance
    def test_search_assignable_users_for_issues_by_issue(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_ADMIN,
                                                             issueKey=self.issue)
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_issues_by_issue_maxresults(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_ADMIN,
                                                             issueKey=self.issue, maxResults=2)
        self.assertLessEqual(len(users), 2)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_assignable_users_for_issues_by_issue_startat(self):
        users = self.jira.search_assignable_users_for_issues(self.test_manager.CI_JIRA_ADMIN,
                                                             issueKey=self.issue, startAt=2)
        self.assertGreaterEqual(len(users), 0)

    @pytest.mark.xfail(reason="Jira may return 500")
    def test_user_avatars(self):
        # Tests the end-to-end user avatar creation process: upload as temporary, confirm after cropping,
        # and selection.
        size = os.path.getsize(TEST_ICON_PATH)
        # filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar(JiraTestManager().CI_JIRA_ADMIN, TEST_ICON_PATH,
                                                      size, icon.read())
        self.assertIn('cropperOffsetX', props)
        self.assertIn('cropperOffsetY', props)
        self.assertIn('cropperWidth', props)
        self.assertTrue(props['needsCropping'])

        props['needsCropping'] = False
        avatar_props = self.jira.confirm_user_avatar(JiraTestManager().CI_JIRA_ADMIN, props)
        self.assertIn('id', avatar_props)
        self.assertEqual(avatar_props['owner'], JiraTestManager().CI_JIRA_ADMIN)

        self.jira.set_user_avatar(JiraTestManager().CI_JIRA_ADMIN, avatar_props['id'])

        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertGreaterEqual(len(avatars['system']), 20)  # observed values between 20-24 so far
        self.assertGreaterEqual(len(avatars['custom']), 1)

    @unittest.skip("broken: set avatar returns 400")
    def test_set_user_avatar(self):
        def find_selected_avatar(avatars):
            for avatar in avatars['system']:
                if avatar['isSelected']:
                    return avatar
            # else:
            #     raise Exception as e
            #     print(e)

        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)

        self.jira.set_user_avatar(self.test_manager.CI_JIRA_ADMIN, avatars['system'][0])
        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(find_selected_avatar(avatars)['id'], avatars['system'][0])

        self.jira.set_user_avatar(self.test_manager.CI_JIRA_ADMIN, avatars['system'][1])
        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(find_selected_avatar(avatars)['id'], avatars['system'][1])

    @unittest.skip("disable until I have permissions to write/modify")
    # WRONG
    def test_delete_user_avatar(self):
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar(self.test_manager.CI_JIRA_ADMIN, filename,
                                                      size, icon.read())
        # print(props)
        self.jira.delete_user_avatar(self.test_manager.CI_JIRA_ADMIN, props['id'])

    def test_search_users(self):
        users = self.jira.search_users(self.test_manager.CI_JIRA_USER)
        self.assertGreaterEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_USER, usernames)

    def test_search_users_maxresults(self):
        users = self.jira.search_users(self.test_manager.CI_JIRA_USER, maxResults=1)
        self.assertGreaterEqual(1, len(users))

    @flaky
    def test_search_allowed_users_for_issue_by_project(self):
        users = self.jira.search_allowed_users_for_issue(self.test_manager.CI_JIRA_USER,
                                                         projectKey=self.project_a)
        self.assertGreaterEqual(len(users), 1)

    @not_on_custom_jira_instance
    def test_search_allowed_users_for_issue_by_issue(self):
        users = self.jira.search_allowed_users_for_issue('a',
                                                         issueKey=self.issue)
        self.assertGreaterEqual(len(users), 1)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_allowed_users_for_issue_maxresults(self):
        users = self.jira.search_allowed_users_for_issue('a',
                                                         projectKey=self.project_b, maxResults=2)
        self.assertLessEqual(len(users), 2)

    @pytest.mark.xfail(reason='query returns empty list')
    def test_search_allowed_users_for_issue_startat(self):
        users = self.jira.search_allowed_users_for_issue('c',
                                                         projectKey=self.project_b, startAt=1)
        self.assertGreaterEqual(len(users), 0)

    def test_add_users_to_set(self):
        users_set = set(
            [self.jira.user(self.test_manager.CI_JIRA_ADMIN), self.jira.user(self.test_manager.CI_JIRA_ADMIN)])
        self.assertEqual(len(users_set), 1)


@flaky
class VersionTests(unittest.TestCase):

    def setUp(self):
        self.manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = JiraTestManager().project_b

    def test_create_version(self):
        name = 'new version ' + self.project_b
        desc = 'test version of ' + self.project_b
        release_date = '2015-03-11'
        version = self.jira.create_version(name,
                                           self.project_b,
                                           releaseDate=release_date,
                                           description=desc)
        self.assertEqual(version.name, name)
        self.assertEqual(version.description, desc)
        self.assertEqual(version.releaseDate, release_date)
        version.delete()

    @flaky
    def test_create_version_with_project_obj(self):
        project = self.jira.project(self.project_b)
        version = self.jira.create_version('new version 2', project,
                                           releaseDate='2015-03-11', description='test version!')
        self.assertEqual(version.name, 'new version 2')
        self.assertEqual(version.description, 'test version!')
        self.assertEqual(version.releaseDate, '2015-03-11')
        version.delete()

    @flaky
    def test_update_version(self):

        version = self.jira.create_version('new updated version 1',
                                           self.project_b, releaseDate='2015-03-11',
                                           description='new to be updated!')
        version.update(name='new updated version name 1',
                       description='new updated!')
        self.assertEqual(version.name, 'new updated version name 1')
        self.assertEqual(version.description, 'new updated!')

        v = self.jira.version(version.id)
        self.assertEqual(v, version)
        self.assertEqual(v.id, version.id)

        version.delete()

    def test_delete_version(self):
        version_str = "test_delete_version:" + self.manager.jid
        version = self.jira.create_version(version_str, self.project_b,
                                           releaseDate='2015-03-11',
                                           description='not long for this world')
        version.delete()
        self.assertRaises(JIRAError, self.jira.version, version.id)

    # def test_version_expandos(self):
    #     pass


@flaky
class OtherTests(unittest.TestCase):

    def test_session_invalid_login(self):
        try:
            JIRA('https://support.atlassian.com',
                 basic_auth=("xxx", "xxx"),
                 validate=True,
                 logging=False)
        except Exception as e:
            self.assertIsInstance(e, JIRAError)
            # 20161010: jira cloud returns 500
            assert e.status_code in (401, 500)
            str(JIRAError)  # to see that this does not raise an exception
            return
        assert False


@flaky
class SessionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_session(self):
        user = self.jira.session()
        self.assertIsNotNone(user.raw['session'])

    def test_session_with_no_logged_in_user_raises(self):
        anon_jira = JIRA('https://support.atlassian.com', logging=False)
        self.assertRaises(JIRAError, anon_jira.session)

    # @pytest.mark.skipif(platform.python_version() < '3', reason='Does not work with Python 2')
    # @not_on_custom_jira_instance  # takes way too long
    def test_session_server_offline(self):
        try:
            JIRA('https://127.0.0.1:1', logging=False, max_retries=0)
        except Exception as e:
            self.assertIn(type(e), (JIRAError, requests.exceptions.ConnectionError, AttributeError), e)
            return
        self.assertTrue(False, "Instantiation of invalid JIRA instance succeeded.")


@flaky
class WebsudoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_kill_websudo(self):
        self.jira.kill_websudo()

    # def test_kill_websudo_without_login_raises(self):
    #    self.assertRaises(ConnectionError, JIRA)


@flaky
class UserAdministrationTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = self.test_manager.jira_admin
        self.test_username = "test_%s" % self.test_manager.project_a
        self.test_email = "%s@example.com" % self.test_username
        self.test_password = rndpassword()
        self.test_groupname = 'testGroupFor_%s' % self.test_manager.project_a

    def test_add_and_remove_user(self):

        try:
            self.jira.delete_user(self.test_username)
        except JIRAError:
            # we ignore if it fails to delete from start because we don't know if it already existed
            pass

        result = self.jira.add_user(
            self.test_username, self.test_email, password=self.test_password)
        assert result, True

        try:
            # Make sure user exists before attempting test to delete.
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password)
        except JIRAError:
            pass

        result = self.jira.delete_user(self.test_username)
        assert result, True

        x = -1
        # avoiding a zombie due to Atlassian caching
        for i in range(10):
            x = self.jira.search_users(self.test_username)
            if len(x) == 0:
                break
            sleep(1)

        self.assertEqual(
            len(x), 0, "Found test user when it should have been deleted. Test Fails.")

    @flaky
    def test_add_group(self):
        try:
            self.jira.remove_group(self.test_groupname)
        except JIRAError:
            pass

        sleep(2)  # avoid 500 errors like https://travis-ci.org/pycontribs/jira/jobs/176544578#L552
        result = self.jira.add_group(self.test_groupname)
        assert result, True

        x = self.jira.groups(query=self.test_groupname)
        self.assertEqual(self.test_groupname, x[0], "Did not find expected group after trying to add"
                                                    " it. Test Fails.")
        self.jira.remove_group(self.test_groupname)

    def test_remove_group(self):
        try:
            self.jira.add_group(self.test_groupname)
            sleep(1)  # avoid 400: https://travis-ci.org/pycontribs/jira/jobs/176539521#L395
        except JIRAError:
            pass

        result = self.jira.remove_group(self.test_groupname)
        assert result, True

        x = -1
        for i in range(5):
            x = self.jira.groups(query=self.test_groupname)
            if x == 0:
                break
            sleep(1)

        self.assertEqual(len(
            x), 0, 'Found group with name when it should have been deleted. Test Fails.')

    @not_on_custom_jira_instance
    @pytest.mark.xfail(reason="query may return empty list: https://travis-ci.org/pycontribs/jira/jobs/191274505#L520")
    def test_add_user_to_group(self):
        try:
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password)
            self.jira.add_group(self.test_groupname)
            # Just in case user is already there.
            self.jira.remove_user_from_group(
                self.test_username, self.test_groupname)
        except JIRAError:
            pass

        result = self.jira.add_user_to_group(
            self.test_username, self.test_groupname)
        assert result, True

        x = self.jira.group_members(self.test_groupname)
        self.assertIn(self.test_username, x.keys(),
                      'Username not returned in group member list. Test Fails.')
        self.assertIn('email', x[self.test_username])
        self.assertIn('fullname', x[self.test_username])
        self.assertIn('active', x[self.test_username])
        self.jira.remove_group(self.test_groupname)
        self.jira.delete_user(self.test_username)

    def test_remove_user_from_group(self):
        try:
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password)
        except JIRAError:
            pass

        try:
            self.jira.add_group(self.test_groupname)
        except JIRAError:
            pass

        try:
            self.jira.add_user_to_group(
                self.test_username, self.test_groupname)
        except JIRAError:
            pass

        result = self.jira.remove_user_from_group(
            self.test_username, self.test_groupname)
        assert result, True

        sleep(2)
        x = self.jira.group_members(self.test_groupname)
        self.assertNotIn(self.test_username, x.keys(), 'Username found in group when it should have been removed. '
                                                       'Test Fails.')

        self.jira.remove_group(self.test_groupname)
        self.jira.delete_user(self.test_username)


@flaky
class ServiceDeskTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = self.test_manager.jira_admin
        self.test_fullname = "TestCustomerFullName %s" % self.test_manager.project_a
        self.test_email = "test_customer_%s@example.com" % self.test_manager.project_a
        self.test_organization_name = "test_organization_%s" % self.test_manager.project_a

    def test_create_and_delete_customer(self):
        try:
            self.jira.delete_user(self.test_email)
        except JIRAError:
            pass

        customer = self.jira.create_customer(self.test_email, self.test_fullname)
        assert customer.emailAddress, self.test_email
        assert customer.displayName, self.test_fullname

        result = self.jira.delete_user(self.test_email)
        assert result, True

        x = -1
        # avoiding a zombie due to Atlassian caching
        for i in range(10):
            x = self.jira.search_users(self.test_email)
            if len(x) == 0:
                break
            sleep(1)

        self.assertEqual(len(x), 0, "Found test user when it should have been deleted. Test Fails.")

    def test_get_servicedesk_info(self):
        result = self.jira.servicedesk_info()
        self.assertNotEquals(result, False)

    def test_create_and_delete_organization(self):
        organization = self.jira.create_organization(self.test_organization_name)
        assert organization.name, self.test_organization_name

        result = self.jira.delete_organization(organization.id)
        assert result, True



class JiraShellTests(unittest.TestCase):

    def test_jirashell_command_exists(self):
        result = os.system('jirashell --help')
        self.assertEqual(result, 0)


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
