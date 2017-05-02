#!/usr/bin/env python
from __future__ import print_function
import getpass
import hashlib
import logging
import os
import re
import sys
from time import sleep
import traceback

import py
from tenacity import retry
from tenacity import stop_after_attempt

from jira import JIRA  # noqa


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
                self.project_c = self.jid + 'C'  # For Service Desk
                self.project_c_name = "Test user=%s key=%s C" \
                                      % (getpass.getuser(), self.project_c)

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

                try:
                    self.jira_admin.project(self.project_c)
                except Exception as e:
                    logging.warning(e)
                    pass
                else:
                    try:
                        self.jira_admin.delete_project(self.project_c)
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

                # Create project for Jira Service Desk
                try:
                    self.jira_admin.create_project(self.project_c,
                                                   self.project_c_name,
                                                   template_name='IT Service Desk')
                except Exception:
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
