#!/usr/bin/env python
from __future__ import print_function
import os
import re
import sys
import logging
import getpass
import random
import string
import inspect
import platform
from time import sleep

import py
import pytest

if platform.python_version() < '3':
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
except:
    pass

if 'CI_JIRA_URL' in os.environ:
    not_on_custom_jira_instance = pytest.mark.skipif(
        True, reason="Not applicable for custom JIRA instance"
    )
    logging.info('Picked up custom JIRA engine.')
else:
    def noop(arg):
        return arg
    not_on_custom_jira_instance = noop


def rndstr():
    return ''.join(random.sample(string.ascii_letters, 6))


def rndpassword():
    # generates a password of lengh 14
    s = ''.join(random.sample(string.ascii_uppercase, 5)) + \
        ''.join(random.sample(string.ascii_lowercase, 5)) + \
        ''.join(random.sample(string.digits, 2)) + \
        ''.join(random.sample('~`!@#$%^&*()_+-=[]\\{}|;\':<>?,./', 2))
    return ''.join(random.sample(s, len(s)))


class Singleton(type):

    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class JiraTestManager(object):
    """
    Used to instantiate and populate the JIRA instance with data used by the unit tests.

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

    # TODO: Remove, not relevant for pytest as this class is in "session"
    # fixture
    __shared_state = {}

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

                prefix = 'Z' + (re.sub("[^A-Z]", "",
                                       getpass.getuser().upper()))[0:6] + \
                         str(sys.version_info[0]) + \
                         str(sys.version_info[1])

                self.project_a = prefix + 'A'  # old XSS
                self.project_a_name = "Test user=%s key=%s A" \
                                      % (getpass.getuser(), self.project_a)
                self.project_b = prefix + 'B'  # old BULK
                self.project_b_name = "Test user=%s key=%s B" \
                                      % (getpass.getuser(), self.project_b)

                # TODO: fin a way to prevent SecurityTokenMissing for On Demand
                # https://jira.atlassian.com/browse/JRA-39153
                try:
                    self.jira_admin.project(self.project_a)
                except Exception as e:
                    logging.warning(e)
                    pass
                else:
                    self.jira_admin.delete_project(self.project_a)

                try:
                    self.jira_admin.project(self.project_b)
                except Exception as e:
                    logging.warning(e)
                    pass
                else:
                    self.jira_admin.delete_project(self.project_b)

                sleep(1)
                # try:
                self.jira_admin.create_project(self.project_a,
                                               self.project_a_name)
                self.project_a_id = self.jira_admin.project(self.project_a).id
                # except Exception as e:
                #    logging.warning("Got %s" % e)
                # try:
                # assert self.jira_admin.create_project(self.project_b,
                # self.project_b_name) is  True, "Failed to create %s" %
                # self.project_b
                self.jira_admin.create_project(self.project_b,
                                               self.project_b_name)
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

            except Exception:
                logging.exception("Basic test setup failed")
                self.initialized = 1
                py.test.exit("FATAL")

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


@pytest.mark.skipif(True,
                    reason="Skipped due to "
                    "https://jira.atlassian.com/browse/JRA-59619")
class SecurityLevelTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_security_level(self):
        # This is hardcoded due to Atlassian bug: https://jira.atlassian.com/browse/JRA-59619
        sec_level = self.jira.security_level('10000')
        self.assertEqual(sec_level.id, '10000')


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
