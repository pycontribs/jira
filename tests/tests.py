#!/usr/bin/env python
"""This file contains tests that do not fit into any specific file yet.

Feel free to make your own test file if appropriate.

Refer to conftest.py for shared helper methods.

resources/test_* : For tests related to resources
test_* : For other tests of the non-resource elements of the jira package.
"""
import logging
import os
import pickle
from time import sleep
from typing import cast
from unittest import mock

import pytest
import requests

from jira import JIRA, Issue, JIRAError
from jira.client import ResultList
from jira.resources import cls_for_resource
from tests.conftest import JiraTestCase, rndpassword

LOGGER = logging.getLogger(__name__)


class UniversalResourceTests(JiraTestCase):
    def test_universal_find_existing_resource(self):
        resource = self.jira.find("issue/{0}", self.test_manager.project_b_issue1)
        issue = self.jira.issue(self.test_manager.project_b_issue1)
        self.assertEqual(resource.self, issue.self)
        self.assertEqual(resource.key, issue.key)

    def test_find_invalid_resource_raises_exception(self):
        with self.assertRaises(JIRAError) as cm:
            self.jira.find("woopsydoodle/{0}", "666")

        ex = cm.exception
        assert ex.status_code in [400, 404]
        self.assertIsNotNone(ex.text)
        self.assertRegex(ex.url, "^https?://.*/rest/api/(2|latest)/woopsydoodle/666$")

    def test_pickling_resource(self):
        resource = self.jira.find("issue/{0}", self.test_manager.project_b_issue1)

        pickled = pickle.dumps(resource.raw)
        unpickled = pickle.loads(pickled)
        cls = cls_for_resource(unpickled["self"])
        unpickled_instance = cls(
            self.jira._options, self.jira._session, raw=pickle.loads(pickled)
        )
        self.assertEqual(resource.key, unpickled_instance.key)
        # Class types are no longer equal, cls_for_resource() returns an Issue type
        # find() returns a Resource type. So we compare the raw json
        self.assertEqual(resource.raw, unpickled_instance.raw)

    def test_pickling_resource_class(self):
        resource = self.jira.find("issue/{0}", self.test_manager.project_b_issue1)

        pickled = pickle.dumps(resource)
        unpickled = pickle.loads(pickled)

        self.assertEqual(resource.key, unpickled.key)
        self.assertEqual(resource, unpickled)

    def test_pickling_issue_class(self):
        resource = self.test_manager.project_b_issue1_obj

        pickled = pickle.dumps(resource)
        unpickled = pickle.loads(pickled)

        self.assertEqual(resource.key, unpickled.key)
        self.assertEqual(resource, unpickled)

    def test_bad_attribute(self):
        resource = self.jira.find("issue/{0}", self.test_manager.project_b_issue1)

        with self.assertRaises(AttributeError):
            getattr(resource, "bogus123")

    def test_hashable(self):
        resource = self.jira.find("issue/{0}", self.test_manager.project_b_issue1)
        resource2 = self.jira.find("issue/{0}", self.test_manager.project_b_issue2)

        r1_hash = hash(resource)
        r2_hash = hash(resource2)

        assert r1_hash != r2_hash

        dict_of_resource = {resource: "hey", resource2: "peekaboo"}
        dict_of_resource.update({resource: "hey ho"})

        assert len(dict_of_resource.keys()) == 2
        assert {resource, resource2} == set(dict_of_resource.keys())
        assert dict_of_resource[resource] == "hey ho"

    def test_hashable_issue_object(self):
        resource = self.test_manager.project_b_issue1_obj
        resource2 = self.test_manager.project_b_issue2_obj

        r1_hash = hash(resource)
        r2_hash = hash(resource2)

        assert r1_hash != r2_hash

        dict_of_resource = {resource: "hey", resource2: "peekaboo"}
        dict_of_resource.update({resource: "hey ho"})

        assert len(dict_of_resource.keys()) == 2
        assert {resource, resource2} == set(dict_of_resource.keys())
        assert dict_of_resource[resource] == "hey ho"


class ApplicationPropertiesTests(JiraTestCase):
    def test_application_properties(self):
        props = self.jira.application_properties()
        for p in props:
            self.assertIsInstance(p, dict)
            self.assertTrue(
                set(p.keys()).issuperset(set(["type", "name", "value", "key", "id"]))
            )

    def test_application_property(self):
        clone_prefix = self.jira.application_properties(
            key="jira.lf.text.headingcolour"
        )
        self.assertEqual(clone_prefix["value"], "#172b4d")

    def test_set_application_property(self):
        prop = "jira.lf.favicon.hires.url"
        valid_value = "/jira-favicon-hires.png"
        invalid_value = "/invalid-jira-favicon-hires.png"

        self.jira.set_application_property(prop, invalid_value)
        self.assertEqual(
            self.jira.application_properties(key=prop)["value"], invalid_value
        )
        self.jira.set_application_property(prop, valid_value)
        self.assertEqual(
            self.jira.application_properties(key=prop)["value"], valid_value
        )

    def test_setting_bad_property_raises(self):
        prop = "random.nonexistent.property"
        self.assertRaises(JIRAError, self.jira.set_application_property, prop, "666")


class FieldsTests(JiraTestCase):
    def test_fields(self):
        fields = self.jira.fields()
        self.assertGreater(len(fields), 10)


class MyPermissionsTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1

    def test_my_permissions(self):
        perms = self.jira.my_permissions()
        self.assertGreaterEqual(len(perms["permissions"]), 40)

    def test_my_permissions_by_project(self):
        perms = self.jira.my_permissions(projectKey=self.test_manager.project_a)
        self.assertGreaterEqual(len(perms["permissions"]), 10)
        perms = self.jira.my_permissions(projectId=self.test_manager.project_a_id)
        self.assertGreaterEqual(len(perms["permissions"]), 10)

    def test_my_permissions_by_issue(self):
        perms = self.jira.my_permissions(issueKey=self.issue_1)
        self.assertGreaterEqual(len(perms["permissions"]), 10)
        perms = self.jira.my_permissions(
            issueId=self.test_manager.project_b_issue1_obj.id
        )
        self.assertGreaterEqual(len(perms["permissions"]), 10)


class SearchTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue = self.test_manager.project_b_issue1

    def test_search_issues(self):
        issues = self.jira.search_issues("project=%s" % self.project_b)
        issues = cast(ResultList[Issue], issues)
        self.assertLessEqual(len(issues), 50)  # default maxResults
        for issue in issues:
            self.assertTrue(issue.key.startswith(self.project_b))

    def test_search_issues_async(self):
        original_val = self.jira._options["async"]
        try:
            self.jira._options["async"] = True
            issues = self.jira.search_issues(
                "project=%s" % self.project_b, maxResults=False
            )
            issues = cast(ResultList[Issue], issues)
            self.assertEqual(len(issues), issues.total)
            for issue in issues:
                self.assertTrue(issue.key.startswith(self.project_b))
        finally:
            self.jira._options["async"] = original_val

    def test_search_issues_maxresults(self):
        issues = self.jira.search_issues("project=%s" % self.project_b, maxResults=10)
        self.assertLessEqual(len(issues), 10)

    def test_search_issues_startat(self):
        issues = self.jira.search_issues(
            "project=%s" % self.project_b, startAt=2, maxResults=10
        )
        self.assertGreaterEqual(len(issues), 1)
        # we know that project_b should have at least 3 issues

    def test_search_issues_field_limiting(self):
        issues = self.jira.search_issues(
            "key=%s" % self.issue, fields="summary,comment"
        )
        issues = cast(ResultList[Issue], issues)
        self.assertTrue(hasattr(issues[0].fields, "summary"))
        self.assertTrue(hasattr(issues[0].fields, "comment"))
        self.assertFalse(hasattr(issues[0].fields, "reporter"))
        self.assertFalse(hasattr(issues[0].fields, "progress"))

    def test_search_issues_expand(self):
        issues = self.jira.search_issues("key=%s" % self.issue, expand="changelog")
        issues = cast(ResultList[Issue], issues)
        # self.assertTrue(hasattr(issues[0], 'names'))
        self.assertEqual(len(issues), 1)
        self.assertFalse(hasattr(issues[0], "editmeta"))
        self.assertTrue(hasattr(issues[0], "changelog"))
        self.assertEqual(issues[0].key, self.issue)


class ServerInfoTests(JiraTestCase):
    def test_server_info(self):
        server_info = self.jira.server_info()
        self.assertIn("baseUrl", server_info)
        self.assertIn("version", server_info)


class OtherTests(JiraTestCase):
    def setUp(self) -> None:
        pass  # we don't need Jira instance here

    def test_session_invalid_login(self):
        try:
            JIRA(
                "https://jira.atlassian.com",
                basic_auth=("xxx", "xxx"),
                validate=True,
                logging=False,
            )
        except Exception as e:
            self.assertIsInstance(e, JIRAError)
            e = cast(JIRAError, e)  # help mypy
            # 20161010: jira cloud returns 500
            assert e.status_code in (401, 500, 403)
            str(JIRAError)  # to see that this does not raise an exception
            return
        assert False


class SessionTests(JiraTestCase):
    def test_session(self):
        user = self.jira.session()
        self.assertIsNotNone(user.raw["self"])
        self.assertIsNotNone(user.raw["name"])

    def test_session_with_no_logged_in_user_raises(self):
        anon_jira = JIRA("https://jira.atlassian.com", logging=False)
        self.assertRaises(JIRAError, anon_jira.session)

    def test_session_server_offline(self):
        try:
            JIRA("https://127.0.0.1:1", logging=False, max_retries=0)
        except Exception as e:
            self.assertIn(
                type(e),
                (JIRAError, requests.exceptions.ConnectionError, AttributeError),
                e,
            )
            return
        self.assertTrue(False, "Instantiation of invalid JIRA instance succeeded.")


class AsyncTests(JiraTestCase):
    def setUp(self):
        self.jira = JIRA(
            "https://jira.atlassian.com",
            logging=False,
            async_=True,
            validate=False,
            get_server_info=False,
        )

    def test_fetch_pages(self):
        """Tests that the JIRA._fetch_pages method works as expected."""
        params = {"startAt": 0}
        total = 26
        expected_results = []
        for i in range(0, total):
            result = _create_issue_result_json(i, "summary %s" % i, key="KEY-%s" % i)
            expected_results.append(result)
        result_one = _create_issue_search_results_json(
            expected_results[:10], max_results=10, total=total
        )
        result_two = _create_issue_search_results_json(
            expected_results[10:20], max_results=10, total=total
        )
        result_three = _create_issue_search_results_json(
            expected_results[20:], max_results=6, total=total
        )
        mock_session = mock.Mock(name="mock_session")
        responses = mock.Mock(name="responses")
        responses.content = "_filler_"
        responses.json.side_effect = [result_one, result_two, result_three]
        responses.status_code = 200
        mock_session.request.return_value = responses
        mock_session.get.return_value = responses
        self.jira._session.close()
        self.jira._session = mock_session
        items = self.jira._fetch_pages(Issue, "issues", "search", 0, False, params)
        self.assertEqual(len(items), total)
        self.assertEqual(
            set(item.key for item in items),
            set(expected_r["key"] for expected_r in expected_results),
        )


def _create_issue_result_json(issue_id, summary, key, **kwargs):
    """Returns a minimal json object for an issue."""
    return {
        "id": "%s" % issue_id,
        "summary": summary,
        "key": key,
        "self": kwargs.get("self", "http://example.com/%s" % issue_id),
    }


def _create_issue_search_results_json(issues, **kwargs):
    """Returns a minimal json object for Jira issue search results."""
    return {
        "startAt": kwargs.get("start_at", 0),
        "maxResults": kwargs.get("max_results", 50),
        "total": kwargs.get("total", len(issues)),
        "issues": issues,
    }


class WebsudoTests(JiraTestCase):
    def test_kill_websudo(self):
        self.jira.kill_websudo()

    # def test_kill_websudo_without_login_raises(self):
    #    self.assertRaises(ConnectionError, JIRA)


class UserAdministrationTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.test_username = "test_%s" % self.test_manager.project_a
        self.test_email = "%s@example.com" % self.test_username
        self.test_password = rndpassword()
        self.test_groupname = "testGroupFor_%s" % self.test_manager.project_a

    def _skip_pycontribs_instance(self):
        pytest.skip(
            "The current ci jira admin user for "
            "https://pycontribs.atlassian.net lacks "
            "permission to modify users."
        )

    def _should_skip_for_pycontribs_instance(self):
        # return True
        return self.test_manager.CI_JIRA_ADMIN == "ci-admin" and (
            self.test_manager.CI_JIRA_URL == "https://pycontribs.atlassian.net"
        )

    def test_add_and_remove_user(self):
        if self._should_skip_for_pycontribs_instance():
            self._skip_pycontribs_instance()
        try:
            self.jira.delete_user(self.test_username)
        except JIRAError as e:
            print(e)
            # we ignore if it fails to delete from start because we don't know if it already existed
            pass

        result = self.jira.add_user(
            self.test_username, self.test_email, password=self.test_password
        )
        assert result, True

        try:
            # Make sure user exists before attempting test to delete.
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password
            )
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
            len(x), 0, "Found test user when it should have been deleted. Test Fails."
        )

        # test creating users with no application access (used for Service Desk)
        result = self.jira.add_user(
            self.test_username,
            self.test_email,
            password=self.test_password,
            application_keys=["jira-software"],
        )
        assert result, True

        result = self.jira.delete_user(self.test_username)
        assert result, True

    def test_add_group(self):
        if self._should_skip_for_pycontribs_instance():
            self._skip_pycontribs_instance()
        try:
            self.jira.remove_group(self.test_groupname)
        except JIRAError:
            pass

        sleep(2)  # avoid 500 errors
        result = self.jira.add_group(self.test_groupname)
        assert result, True

        x = self.jira.groups(query=self.test_groupname)
        self.assertEqual(
            self.test_groupname,
            x[0],
            "Did not find expected group after trying to add" " it. Test Fails.",
        )
        self.jira.remove_group(self.test_groupname)

    def test_remove_group(self):
        if self._should_skip_for_pycontribs_instance():
            self._skip_pycontribs_instance()
        try:
            self.jira.add_group(self.test_groupname)
            sleep(1)  # avoid 400
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

        self.assertEqual(
            len(x),
            0,
            "Found group with name when it should have been deleted. Test Fails.",
        )

    def test_add_user_to_group(self):
        try:
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password
            )
            self.jira.add_group(self.test_groupname)
            # Just in case user is already there.
            self.jira.remove_user_from_group(self.test_username, self.test_groupname)
        except JIRAError:
            pass

        result = self.jira.add_user_to_group(self.test_username, self.test_groupname)
        assert result, True

        x = self.jira.group_members(self.test_groupname)
        self.assertIn(
            self.test_username,
            x.keys(),
            "Username not returned in group member list. Test Fails.",
        )
        self.assertIn("email", x[self.test_username])
        self.assertIn("fullname", x[self.test_username])
        self.assertIn("active", x[self.test_username])
        self.jira.remove_group(self.test_groupname)
        self.jira.delete_user(self.test_username)

    def test_remove_user_from_group(self):
        if self._should_skip_for_pycontribs_instance():
            self._skip_pycontribs_instance()
        try:
            self.jira.add_user(
                self.test_username, self.test_email, password=self.test_password
            )
        except JIRAError:
            pass

        try:
            self.jira.add_group(self.test_groupname)
        except JIRAError:
            pass

        try:
            self.jira.add_user_to_group(self.test_username, self.test_groupname)
        except JIRAError:
            pass

        result = self.jira.remove_user_from_group(
            self.test_username, self.test_groupname
        )
        assert result, True

        sleep(2)
        x = self.jira.group_members(self.test_groupname)
        self.assertNotIn(
            self.test_username,
            x.keys(),
            "Username found in group when it should have been removed. " "Test Fails.",
        )

        self.jira.remove_group(self.test_groupname)
        self.jira.delete_user(self.test_username)


class JiraShellTests(JiraTestCase):
    def setUp(self) -> None:
        pass  # Jira Instance not required

    def test_jirashell_command_exists(self):
        result = os.system("jirashell --help")
        self.assertEqual(result, 0)
