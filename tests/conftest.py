import getpass
import hashlib
import logging
import os
import random
import re
import string
import sys
import unittest
from time import sleep
from typing import Any, Dict

import pytest
from flaky import flaky

from jira import JIRA

TEST_ROOT = os.path.dirname(__file__)
TEST_ICON_PATH = os.path.join(TEST_ROOT, "icon.png")
TEST_ATTACH_PATH = os.path.join(TEST_ROOT, "tests.py")

LOGGER = logging.getLogger(__name__)

OAUTH = False
CONSUMER_KEY = "oauth-consumer"
KEY_CERT_FILE = "/home/bspeakmon/src/atlassian-oauth-examples/rsa.pem"
KEY_CERT_DATA = None
try:
    with open(KEY_CERT_FILE, "r") as cert:
        KEY_CERT_DATA = cert.read()
    OAUTH = True
except Exception:
    OAUTH = False


ON_CUSTOM_JIRA = "CI_JIRA_URL" in os.environ


not_on_custom_jira_instance = pytest.mark.skipif(
    ON_CUSTOM_JIRA, reason="Not applicable for custom Jira instance"
)
if ON_CUSTOM_JIRA:
    LOGGER.info("Picked up custom Jira engine.")


broken_test = pytest.mark.xfail


@flaky  # all have default flaki-ness
class JiraTestCase(unittest.TestCase):
    """Test case for all Jira tests.

    This is the base class for all Jira tests that require access to the
    Jira instance.

    It calls JiraTestManager() in the setUp() method.
    setUp() is the method that is called **before** each test is run.

    Where possible follow the:

    * GIVEN - where you set up any pre-requisites e.g. the expected result
    * WHEN  - where you perform the action and obtain the result
    * THEN  - where you assert the expectation vs the result

    format for tests.
    """

    jira: JIRA  # admin authenticated
    jira_normal: JIRA  # non-admin authenticated

    def setUp(self) -> None:
        """
        This is called before each test. If you want to add more for your tests,
        Run `JiraTestCase.setUp(self) in your custom setUp() to obtain these.
        """
        self.test_manager = JiraTestManager()
        self.jira = self.test_manager.jira_admin
        self.jira_normal = self.test_manager.jira_normal
        self.user_admin = self.test_manager.user_admin
        self.user_normal = self.test_manager.user_normal  # use this user where possible
        self.project_b = self.test_manager.project_b
        self.project_a = self.test_manager.project_a


def rndstr():
    return "".join(random.sample(string.ascii_lowercase, 6))


def rndpassword():
    # generates a password of length 14
    s = (
        "".join(random.sample(string.ascii_uppercase, 5))
        + "".join(random.sample(string.ascii_lowercase, 5))
        + "".join(random.sample(string.digits, 2))
        + "".join(random.sample("~`!@#$%^&*()_+-=[]\\{}|;':<>?,./", 2))
    )
    return "".join(random.sample(s, len(s)))


def hashify(some_string, max_len=8):
    return hashlib.sha256(some_string.encode("utf-8")).hexdigest()[:8].upper()


def get_unique_project_name():
    user = re.sub("[^A-Z_]", "", getpass.getuser().upper())
    if "GITHUB_ACTION" in os.environ and "GITHUB_RUN_NUMBER" in os.environ:
        # please note that user underline (_) is not supported by
        # Jira even if it is documented as supported.
        return "GH" + hashify(user + os.environ["GITHUB_RUN_NUMBER"])
    identifier = (
        user + chr(ord("A") + sys.version_info[0]) + chr(ord("A") + sys.version_info[1])
    )
    return "Z" + hashify(identifier)


class JiraTestManager(object):
    """Instantiate and populate the JIRA instance with data for tests.

    Attributes:
        CI_JIRA_ADMIN (str): Admin user account name.
        CI_JIRA_USER (str): Limited user account name.
        max_retries (int): number of retries to perform for recoverable HTTP errors.
    """

    __shared_state: Dict[Any, Any] = {}

    def __init__(self, jira_hosted_type="Server"):
        """Instantiate and populate the JIRA instance"""
        self.__dict__ = self.__shared_state

        if not self.__dict__:
            self.initialized = False
            self.max_retries = 5

            if jira_hosted_type and jira_hosted_type == "Cloud":
                self.set_jira_cloud_details()
            else:
                self.set_jira_server_details()

            jira_class_kwargs = {
                "server": self.CI_JIRA_URL,
                "logging": False,
                "validate": True,
                "max_retries": self.max_retries,
            }
            if OAUTH:
                self.set_oauth_logins()
            else:
                self.set_basic_auth_logins(**jira_class_kwargs)

            if not self.jira_admin.current_user():
                self.initialized = True
                sys.exit(3)

            # now we need to create some data to start with for the tests
            self.create_some_data()

        if not hasattr(self, "jira_normal") or not hasattr(self, "jira_admin"):
            pytest.exit("FATAL: WTF!?")

        self.user_admin = self.jira_admin.search_users(self.CI_JIRA_ADMIN)[0]
        self.user_normal = self.jira_admin.search_users(self.CI_JIRA_USER)[0]
        self.initialized = True

    def set_jira_cloud_details(self):
        self.CI_JIRA_URL = "https://pycontribs.atlassian.net"
        self.CI_JIRA_ADMIN = "ci-admin"
        self.CI_JIRA_ADMIN_PASSWORD = "sd4s3dgec5fhg4tfsds3434"
        self.CI_JIRA_USER = "ci-user"
        self.CI_JIRA_USER_PASSWORD = "sd4s3dgec5fhg4tfsds3434"

    def set_jira_server_details(self):
        self.CI_JIRA_URL = os.environ["CI_JIRA_URL"]
        self.CI_JIRA_ADMIN = os.environ["CI_JIRA_ADMIN"]
        self.CI_JIRA_ADMIN_PASSWORD = os.environ["CI_JIRA_ADMIN_PASSWORD"]
        self.CI_JIRA_USER = os.environ["CI_JIRA_USER"]
        self.CI_JIRA_USER_PASSWORD = os.environ["CI_JIRA_USER_PASSWORD"]
        self.CI_JIRA_ISSUE = os.environ.get("CI_JIRA_ISSUE", "Bug")

    def set_oauth_logins(self):
        self.jira_admin = JIRA(
            oauth={
                "access_token": "hTxcwsbUQiFuFALf7KZHDaeAJIo3tLUK",
                "access_token_secret": "aNCLQFP3ORNU6WY7HQISbqbhf0UudDAf",
                "consumer_key": CONSUMER_KEY,
                "key_cert": KEY_CERT_DATA,
            }
        )
        self.jira_sysadmin = JIRA(
            oauth={
                "access_token": "4ul1ETSFo7ybbIxAxzyRal39cTrwEGFv",
                "access_token_secret": "K83jBZnjnuVRcfjBflrKyThJa0KSjSs2",
                "consumer_key": CONSUMER_KEY,
                "key_cert": KEY_CERT_DATA,
            },
            logging=False,
            max_retries=self.max_retries,
        )
        self.jira_normal = JIRA(
            oauth={
                "access_token": "ZVDgYDyIQqJY8IFlQ446jZaURIz5ECiB",
                "access_token_secret": "5WbLBybPDg1lqqyFjyXSCsCtAWTwz1eD",
                "consumer_key": CONSUMER_KEY,
                "key_cert": KEY_CERT_DATA,
            }
        )

    def set_basic_auth_logins(self, **jira_class_kwargs):
        if self.CI_JIRA_ADMIN:
            self.jira_admin = JIRA(
                basic_auth=(self.CI_JIRA_ADMIN, self.CI_JIRA_ADMIN_PASSWORD),
                **jira_class_kwargs,
            )
            self.jira_sysadmin = JIRA(
                basic_auth=(self.CI_JIRA_ADMIN, self.CI_JIRA_ADMIN_PASSWORD),
                **jira_class_kwargs,
            )
            self.jira_normal = JIRA(
                basic_auth=(self.CI_JIRA_USER, self.CI_JIRA_USER_PASSWORD),
                **jira_class_kwargs,
            )
        else:
            # Setup some un-authenticated users
            self.jira_admin = JIRA(self.CI_JIRA_URL, **jira_class_kwargs)
            self.jira_sysadmin = JIRA(self.CI_JIRA_URL, **jira_class_kwargs)
            self.jira_normal = JIRA(self.CI_JIRA_URL, **jira_class_kwargs)

    def create_some_data(self):
        """Create some data for the tests"""

        # jira project key is max 10 chars, no letter.
        # [0] always "Z"
        # [1-6] username running the tests (hope we will not collide)
        # [7-8] python version A=0, B=1,..
        # [9] A,B -- we may need more than one project

        """ `jid` is important for avoiding concurrency problems when
        executing tests in parallel as we have only one test instance.

        jid length must be less than 9 characters because we may append
        another one and the Jira Project key length limit is 10.
        """

        self.jid = get_unique_project_name()

        self.project_a = self.jid + "A"  # old XSS
        self.project_a_name = "Test user=%s key=%s A" % (
            getpass.getuser(),
            self.project_a,
        )
        self.project_b = self.jid + "B"  # old BULK
        self.project_b_name = "Test user=%s key=%s B" % (
            getpass.getuser(),
            self.project_b,
        )
        self.project_sd = self.jid + "C"
        self.project_sd_name = "Test user=%s key=%s C" % (
            getpass.getuser(),
            self.project_sd,
        )

        # TODO(ssbarnea): find a way to prevent SecurityTokenMissing for On Demand
        # https://jira.atlassian.com/browse/JRA-39153
        try:
            self.jira_admin.project(self.project_a)
        except Exception as e:
            LOGGER.warning(e)
        else:
            try:
                self.jira_admin.delete_project(self.project_a)
            except Exception as e:
                LOGGER.warning("Failed to delete %s\n%s", self.project_a, e)

        try:
            self.jira_admin.project(self.project_b)
        except Exception as e:
            LOGGER.warning(e)
        else:
            try:
                self.jira_admin.delete_project(self.project_b)
            except Exception as e:
                LOGGER.warning("Failed to delete %s\n%s", self.project_b, e)

        # wait for the project to be deleted
        for _ in range(1, 20):
            try:
                self.jira_admin.project(self.project_b)
            except Exception:
                break
            print("Warning: Project not deleted yet....")
            sleep(2)

        for _ in range(6):
            try:
                if self.jira_admin.create_project(self.project_a, self.project_a_name):
                    break
            except Exception as e:
                if "A project with that name already exists" not in str(e):
                    raise e
        self.project_a_id = self.jira_admin.project(self.project_a).id
        self.jira_admin.create_project(self.project_b, self.project_b_name)

        try:
            self.jira_admin.create_project(self.project_b, self.project_b_name)
        except Exception:
            # we care only for the project to exist
            pass
        sleep(1)  # keep it here as often Jira will report the
        # project as missing even after is created
        self.project_b_issue1_obj = self.jira_admin.create_issue(
            project=self.project_b,
            summary="issue 1 from %s" % self.project_b,
            issuetype=self.CI_JIRA_ISSUE,
        )
        self.project_b_issue1 = self.project_b_issue1_obj.key

        self.project_b_issue2_obj = self.jira_admin.create_issue(
            project=self.project_b,
            summary="issue 2 from %s" % self.project_b,
            issuetype={"name": self.CI_JIRA_ISSUE},
        )
        self.project_b_issue2 = self.project_b_issue2_obj.key

        self.project_b_issue3_obj = self.jira_admin.create_issue(
            project=self.project_b,
            summary="issue 3 from %s" % self.project_b,
            issuetype={"name": self.CI_JIRA_ISSUE},
        )
        self.project_b_issue3 = self.project_b_issue3_obj.key


def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item["key"] == key:
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
        if seq_item["name"] == name:
            return seq_item
