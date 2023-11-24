from __future__ import annotations

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
from typing import Any

import pytest

from jira_svc import jira_svc
from jira_svc.exceptions import jira_svcError

TEST_ROOT = os.path.dirname(__file__)
TEST_ICON_PATH = os.path.join(TEST_ROOT, "icon.png")
TEST_ATTACH_PATH = os.path.join(TEST_ROOT, "tests.py")

LOGGER = logging.getLogger(__name__)


allow_on_cloud = pytest.mark.allow_on_cloud
broken_test = pytest.mark.xfail


class jira_svcTestCase(unittest.TestCase):
    """Test case for all jira_svc tests.

    This is the base class for all jira_svc tests that require access to the
    jira_svc instance.

    It calls jira_svcTestManager() in the setUp() method.
    setUp() is the method that is called **before** each test is run.

    Where possible follow the:

    * GIVEN - where you set up any pre-requisites e.g. the expected result
    * WHEN  - where you perform the action and obtain the result
    * THEN  - where you assert the expectation vs the result

    format for tests.
    """

    jira_svc: jira_svc  # admin authenticated
    jira_svc_normal: jira_svc  # non-admin authenticated

    def setUp(self) -> None:
        """
        This is called before each test. If you want to add more for your tests,
        Run `super().setUp() in your custom setUp() to obtain these.
        """

        initialized = False
        try:
            self.test_manager = jira_svcTestManager()
            initialized = self.test_manager.initialized
        except Exception as e:
            # pytest with flaky swallows any exceptions re-raised in a try, except
            # so we log any exceptions for aiding debugging
            LOGGER.exception(e)
        self.assertTrue(initialized, "Test Manager setUp failed")

        self.jira_svc = self.test_manager.jira_svc_admin
        self.jira_svc_normal = self.test_manager.jira_svc_normal
        self.user_admin = self.test_manager.user_admin
        self.user_normal = self.test_manager.user_normal  # use this user where possible
        self.project_b = self.test_manager.project_b
        self.project_a = self.test_manager.project_a

    @property
    def identifying_user_property(self) -> str:
        """Literal["accountId", "name"]: Depending on if jira_svc Cloud or Server"""
        return "accountId" if self.is_jira_svc_cloud_ci else "name"

    @property
    def is_jira_svc_cloud_ci(self) -> bool:
        """is running on jira_svc Cloud"""
        return self.test_manager._cloud_ci


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
        # jira_svc even if it is documented as supported.
        return "GH" + hashify(user + os.environ["GITHUB_RUN_NUMBER"])
    identifier = (
        user + chr(ord("A") + sys.version_info[0]) + chr(ord("A") + sys.version_info[1])
    )
    return "Z" + hashify(identifier)


class jira_svcTestManager:
    """Instantiate and populate the jira_svc instance with data for tests.

    Attributes:
        CI_jira_svc_ADMIN (str): Admin user account name.
        CI_jira_svc_USER (str): Limited user account name.
        max_retries (int): number of retries to perform for recoverable HTTP errors.
        initialized (bool): if init was successful.
    """

    __shared_state: dict[Any, Any] = {}

    def __init__(self, jira_svc_hosted_type=os.environ.get("CI_jira_svc_TYPE", "Server")):
        """Instantiate and populate the jira_svc instance"""
        self.__dict__ = self.__shared_state

        if not self.__dict__:
            self.initialized = False
            self.max_retries = 5
            self._cloud_ci = False

            if jira_svc_hosted_type and jira_svc_hosted_type.upper() == "CLOUD":
                self.set_jira_svc_cloud_details()
                self._cloud_ci = True
            else:
                self.set_jira_svc_server_details()

            jira_svc_class_kwargs = {
                "server": self.CI_jira_svc_URL,
                "logging": False,
                "validate": True,
                "max_retries": self.max_retries,
            }

            self.set_basic_auth_logins(**jira_svc_class_kwargs)

            if not self.jira_svc_admin.current_user():
                self.initialized = True
                sys.exit(3)

            # now we need to create some data to start with for the tests
            self.create_some_data()

        if not hasattr(self, "jira_svc_normal") or not hasattr(self, "jira_svc_admin"):
            pytest.exit("FATAL: WTF!?")

        if self._cloud_ci:
            self.user_admin = self.jira_svc_admin.search_users(query=self.CI_jira_svc_ADMIN)[0]
            self.user_normal = self.jira_svc_admin.search_users(query=self.CI_jira_svc_USER)[0]
        else:
            self.user_admin = self.jira_svc_admin.search_users(self.CI_jira_svc_ADMIN)[0]
            self.user_normal = self.jira_svc_admin.search_users(self.CI_jira_svc_USER)[0]
        self.initialized = True

    def set_jira_svc_cloud_details(self):
        self.CI_jira_svc_URL = "https://pycontribs.atlassian.net"
        self.CI_jira_svc_ADMIN = os.environ["CI_jira_svc_CLOUD_ADMIN"]
        self.CI_jira_svc_ADMIN_PASSWORD = os.environ["CI_jira_svc_CLOUD_ADMIN_TOKEN"]
        self.CI_jira_svc_USER = os.environ["CI_jira_svc_CLOUD_USER"]
        self.CI_jira_svc_USER_PASSWORD = os.environ["CI_jira_svc_CLOUD_USER_TOKEN"]
        self.CI_jira_svc_ISSUE = os.environ.get("CI_jira_svc_ISSUE", "Bug")

    def set_jira_svc_server_details(self):
        self.CI_jira_svc_URL = os.environ["CI_jira_svc_URL"]
        self.CI_jira_svc_ADMIN = os.environ["CI_jira_svc_ADMIN"]
        self.CI_jira_svc_ADMIN_PASSWORD = os.environ["CI_jira_svc_ADMIN_PASSWORD"]
        self.CI_jira_svc_USER = os.environ["CI_jira_svc_USER"]
        self.CI_jira_svc_USER_PASSWORD = os.environ["CI_jira_svc_USER_PASSWORD"]
        self.CI_jira_svc_ISSUE = os.environ.get("CI_jira_svc_ISSUE", "Bug")

    def set_basic_auth_logins(self, **jira_svc_class_kwargs):
        if self.CI_jira_svc_ADMIN:
            self.jira_svc_admin = jira_svc(
                basic_auth=(self.CI_jira_svc_ADMIN, self.CI_jira_svc_ADMIN_PASSWORD),
                **jira_svc_class_kwargs,
            )
            self.jira_svc_sysadmin = jira_svc(
                basic_auth=(self.CI_jira_svc_ADMIN, self.CI_jira_svc_ADMIN_PASSWORD),
                **jira_svc_class_kwargs,
            )
            self.jira_svc_normal = jira_svc(
                basic_auth=(self.CI_jira_svc_USER, self.CI_jira_svc_USER_PASSWORD),
                **jira_svc_class_kwargs,
            )
        else:
            raise RuntimeError("CI_jira_svc_ADMIN environment variable is not set/empty.")

    def _project_exists(self, project_key: str) -> bool:
        """True if we think the project exists, else False.

        Assumes project exists if unknown jira_svc exception is raised.
        """
        try:
            self.jira_svc_admin.project(project_key)
        except jira_svcError as e:  # If the project does not exist a warning is thrown
            if "No project could be found" in str(e):
                return False
            LOGGER.exception("Assuming project '%s' exists.", project_key)
        return True

    def _remove_project(self, project_key):
        """Ensure if the project exists we delete it first"""

        wait_between_checks_secs = 2
        time_to_wait_for_delete_secs = 40
        wait_attempts = int(time_to_wait_for_delete_secs / wait_between_checks_secs)

        # TODO(ssbarnea): find a way to prevent SecurityTokenMissing for On Demand
        # https://jira_svc.atlassian.com/browse/JRA-39153
        if self._project_exists(project_key):
            try:
                self.jira_svc_admin.delete_project(project_key)
            except Exception:
                LOGGER.exception("Failed to delete '%s'.", project_key)

        # wait for the project to be deleted
        for _ in range(1, wait_attempts):
            if not self._project_exists(project_key):
                # If the project does not exist a warning is thrown
                # so once this is raised we know it is deleted successfully
                break
            sleep(wait_between_checks_secs)

        if self._project_exists(project_key):
            raise TimeoutError(
                " Project '{project_key}' not deleted after {time_to_wait_for_delete_secs} seconds"
            )

    def _create_project(
        self, project_key: str, project_name: str, force_recreate: bool = False
    ) -> int:
        """Create a project and return the id"""

        if not force_recreate and self._project_exists(project_key):
            pass
        else:
            self._remove_project(project_key)
            create_attempts = 6
            for _ in range(create_attempts):
                try:
                    if self.jira_svc_admin.create_project(project_key, project_name):
                        break
                except jira_svcError as e:
                    if "A project with that name already exists" not in str(e):
                        raise e
        return self.jira_svc_admin.project(project_key).id

    def create_some_data(self):
        """Create some data for the tests"""

        # jira_svc project key is max 10 chars, no letter.
        # [0] always "Z"
        # [1-6] username running the tests (hope we will not collide)
        # [7-8] python version A=0, B=1,..
        # [9] A,B -- we may need more than one project

        """ `jid` is important for avoiding concurrency problems when
        executing tests in parallel as we have only one test instance.

        jid length must be less than 9 characters because we may append
        another one and the jira_svc Project key length limit is 10.
        """

        self.jid = get_unique_project_name()

        self.project_a = self.jid + "A"  # old XSS
        self.project_a_name = f"Test user={getpass.getuser()} key={self.project_a} A"
        self.project_b = self.jid + "B"  # old BULK
        self.project_b_name = f"Test user={getpass.getuser()} key={self.project_b} B"
        self.project_sd = self.jid + "C"
        self.project_sd_name = f"Test user={getpass.getuser()} key={self.project_sd} C"

        self.project_a_id = self._create_project(self.project_a, self.project_a_name)
        self.project_b_id = self._create_project(
            self.project_b, self.project_b_name, force_recreate=True
        )

        sleep(1)  # keep it here as often jira_svc will report the
        # project as missing even after is created

        project_b_issue_kwargs = {
            "project": self.project_b,
            "issuetype": {"name": self.CI_jira_svc_ISSUE},
        }
        self.project_b_issue1_obj = self.jira_svc_admin.create_issue(
            summary=f"issue 1 from {self.project_b}", **project_b_issue_kwargs
        )
        self.project_b_issue1 = self.project_b_issue1_obj.key

        self.project_b_issue2_obj = self.jira_svc_admin.create_issue(
            summary=f"issue 2 from {self.project_b}", **project_b_issue_kwargs
        )
        self.project_b_issue2 = self.project_b_issue2_obj.key

        self.project_b_issue3_obj = self.jira_svc_admin.create_issue(
            summary=f"issue 3 from {self.project_b}", **project_b_issue_kwargs
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


@pytest.fixture()
def no_fields(monkeypatch):
    """When we want to test the __init__ method of the jira_svc.client.jira_svc
    we don't need any external calls to get the fields.

    We don't need the features of a MagicMock, hence we don't use it here.
    """
    monkeypatch.setattr(jira_svc, "fields", lambda *args, **kwargs: [])
