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
from typing import Optional, cast
from unittest import mock

import pytest
import requests
from parameterized import parameterized

from jira import JIRA, Issue, JIRAError
from jira.client import ResultList
from jira.resources import Dashboard, Resource, cls_for_resource
from tests.conftest import JiraTestCase, allow_on_cloud, rndpassword

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
                set(p.keys()).issuperset({"type", "name", "value", "key", "id"})
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


class MyPermissionsServerTests(JiraTestCase):
    def setUp(self):
        super().setUp()
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


@allow_on_cloud
class MyPermissionsCloudTests(JiraTestCase):
    def setUp(self):
        super().setUp()
        if not self.jira._is_cloud:
            self.skipTest("cloud only test class")
        self.issue_1 = self.test_manager.project_b_issue1
        self.permission_keys = "BROWSE_PROJECTS,CREATE_ISSUES,ADMINISTER_PROJECTS"

    def test_my_permissions(self):
        perms = self.jira.my_permissions(permissions=self.permission_keys)
        self.assertEqual(len(perms["permissions"]), 3)

    def test_my_permissions_by_project(self):
        perms = self.jira.my_permissions(
            projectKey=self.test_manager.project_a, permissions=self.permission_keys
        )
        self.assertEqual(len(perms["permissions"]), 3)
        perms = self.jira.my_permissions(
            projectId=self.test_manager.project_a_id, permissions=self.permission_keys
        )
        self.assertEqual(len(perms["permissions"]), 3)

    def test_my_permissions_by_issue(self):
        perms = self.jira.my_permissions(
            issueKey=self.issue_1, permissions=self.permission_keys
        )
        self.assertEqual(len(perms["permissions"]), 3)
        perms = self.jira.my_permissions(
            issueId=self.test_manager.project_b_issue1_obj.id,
            permissions=self.permission_keys,
        )
        self.assertEqual(len(perms["permissions"]), 3)

    def test_missing_required_param_my_permissions_raises_exception(self):
        with self.assertRaises(JIRAError):
            self.jira.my_permissions()

    def test_invalid_param_my_permissions_raises_exception(self):
        with self.assertRaises(JIRAError):
            self.jira.my_permissions("INVALID_PERMISSION")


class SearchTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue = self.test_manager.project_b_issue1

    def test_search_issues(self):
        issues = self.jira.search_issues(f"project={self.project_b}")
        issues = cast(ResultList[Issue], issues)
        self.assertLessEqual(len(issues), 50)  # default maxResults
        for issue in issues:
            self.assertTrue(issue.key.startswith(self.project_b))

    def test_search_issues_async(self):
        original_val = self.jira._options["async"]
        try:
            self.jira._options["async"] = True
            issues = self.jira.search_issues(
                f"project={self.project_b}", maxResults=False
            )
            issues = cast(ResultList[Issue], issues)
            self.assertEqual(len(issues), issues.total)
            for issue in issues:
                self.assertTrue(issue.key.startswith(self.project_b))
        finally:
            self.jira._options["async"] = original_val

    def test_search_issues_maxresults(self):
        issues = self.jira.search_issues(f"project={self.project_b}", maxResults=10)
        self.assertLessEqual(len(issues), 10)

    def test_search_issues_startat(self):
        issues = self.jira.search_issues(
            f"project={self.project_b}", startAt=2, maxResults=10
        )
        self.assertGreaterEqual(len(issues), 1)
        # we know that project_b should have at least 3 issues

    def test_search_issues_field_limiting(self):
        issues = self.jira.search_issues(f"key={self.issue}", fields="summary,comment")
        issues = cast(ResultList[Issue], issues)
        self.assertTrue(hasattr(issues[0].fields, "summary"))
        self.assertTrue(hasattr(issues[0].fields, "comment"))
        self.assertFalse(hasattr(issues[0].fields, "reporter"))
        self.assertFalse(hasattr(issues[0].fields, "progress"))

    def test_search_issues_expand(self):
        issues = self.jira.search_issues(f"key={self.issue}", expand="changelog")
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


MIMICKED_BACKEND_BATCH_SIZE = 10


class AsyncTests(JiraTestCase):
    def setUp(self):
        self.jira = JIRA(
            "https://jira.atlassian.com",
            logging=False,
            async_=True,
            validate=False,
            get_server_info=False,
        )

    @parameterized.expand(
        [
            (
                0,
                26,
                {Issue: None},
                False,
            ),  # original behaviour, fetch all with jira's original return size
            (0, 26, {Issue: 20}, False),  # set batch size to 20
            (5, 26, {Issue: 20}, False),  # test start_at
            (5, 26, {Issue: 20}, 50),  # test maxResults set (one request)
        ]
    )
    def test_fetch_pages(
        self, start_at: int, total: int, default_batch_sizes: dict, max_results: int
    ):
        """Tests that the JIRA._fetch_pages method works as expected."""
        params = {"startAt": 0}
        self.jira._options["default_batch_size"] = default_batch_sizes
        batch_size = self.jira._get_batch_size(Issue)
        expected_calls = _calculate_calls_for_fetch_pages(
            "https://jira.atlassian.com/rest/api/2/search",
            start_at,
            total,
            max_results,
            batch_size,
            MIMICKED_BACKEND_BATCH_SIZE,
        )
        batch_size = batch_size or MIMICKED_BACKEND_BATCH_SIZE
        expected_results = []
        for i in range(0, total):
            result = _create_issue_result_json(i, f"summary {i}", key=f"KEY-{i}")
            expected_results.append(result)

        if not max_results:
            mocked_api_results = []
            for i in range(start_at, total, batch_size):
                mocked_api_result = _create_issue_search_results_json(
                    expected_results[i : i + batch_size],
                    max_results=batch_size,
                    total=total,
                )
                mocked_api_results.append(mocked_api_result)
        else:
            mocked_api_results = [
                _create_issue_search_results_json(
                    expected_results[start_at : max_results + start_at],
                    max_results=max_results,
                    total=total,
                )
            ]

        mock_session = mock.Mock(name="mock_session")
        responses = mock.Mock(name="responses")
        responses.content = "_filler_"
        responses.json.side_effect = mocked_api_results
        responses.status_code = 200
        mock_session.request.return_value = responses
        mock_session.get.return_value = responses
        self.jira._session.close()
        self.jira._session = mock_session
        items = self.jira._fetch_pages(
            Issue, "issues", "search", start_at, max_results, params=params
        )

        actual_calls = [[kall[1], kall[2]] for kall in self.jira._session.method_calls]
        self.assertEqual(actual_calls, expected_calls)
        self.assertEqual(len(items), total - start_at)
        self.assertEqual(
            {item.key for item in items},
            {expected_r["key"] for expected_r in expected_results[start_at:]},
        )


@pytest.mark.parametrize(
    "default_batch_sizes, item_type, expected",
    [
        ({Issue: 2}, Issue, 2),
        ({Resource: 1}, Resource, 1),
        (
            {Resource: 1, Issue: None},
            Issue,
            None,
        ),
        ({Resource: 1}, Dashboard, 1),
        ({}, Issue, 100),
        ({}, Resource, 100),
    ],
    ids=[
        "modify Issue default",
        "modify Resource default",
        "let backend decide for Issue",
        "fallback",
        "default for Issue",
        "default value for everything else",
    ],
)
def test_get_batch_size(default_batch_sizes, item_type, expected, no_fields):
    jira = JIRA(default_batch_sizes=default_batch_sizes, get_server_info=False)

    assert jira._get_batch_size(item_type) == expected


def _create_issue_result_json(issue_id, summary, key, **kwargs):
    """Returns a minimal json object for an issue."""
    return {
        "id": f"{issue_id}",
        "summary": summary,
        "key": key,
        "self": kwargs.get("self", f"http://example.com/{issue_id}"),
    }


def _create_issue_search_results_json(issues, **kwargs):
    """Returns a minimal json object for Jira issue search results."""
    return {
        "startAt": kwargs.get("start_at", 0),
        "maxResults": kwargs.get("max_results", 50),
        "total": kwargs.get("total", len(issues)),
        "issues": issues,
    }


def _calculate_calls_for_fetch_pages(
    url: str,
    start_at: int,
    total: int,
    max_results: int,
    batch_size: Optional[int],
    default: Optional[int] = 10,
):
    """Returns expected query parameters for specified search-issues arguments."""
    if not max_results:
        call_list = []
        if batch_size is None:
            # for the first request with batch-size is `None` we specifically cannot/don't want to set it but let
            # the server specify it (here we mimic a server-default of 10 issues per batch).
            call_ = [(url,), {"params": {"startAt": start_at}}]
            call_list.append(call_)
            start_at += default
            batch_size = default
        for index, start_at in enumerate(range(start_at, total, batch_size)):
            call_ = [
                (url,),
                {"params": {"startAt": start_at, "maxResults": batch_size}},
            ]

            call_list.append(call_)
    else:
        call_list = [
            [(url,), {"params": {"startAt": start_at, "maxResults": max_results}}]
        ]
    return call_list


DEFAULT_NEW_REMOTE_LINK_OBJECT = {"url": "http://google.com", "title": "googlicious!"}


class ClientRemoteLinkTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_key = self.test_manager.project_b_issue1

    def test_delete_remote_link_by_internal_id(self):
        link = self.jira.add_remote_link(
            self.issue_key,
            destination=DEFAULT_NEW_REMOTE_LINK_OBJECT,
        )
        _id = link.id
        self.jira.delete_remote_link(self.issue_key, internal_id=_id)
        self.assertRaises(JIRAError, self.jira.remote_link, self.issue_key, _id)

    def test_delete_remote_link_by_global_id(self):
        link = self.jira.add_remote_link(
            self.issue_key,
            destination=DEFAULT_NEW_REMOTE_LINK_OBJECT,
            globalId="python-test:story.of.sasquatch.riding",
        )
        _id = link.id
        self.jira.delete_remote_link(
            self.issue_key, global_id="python-test:story.of.sasquatch.riding"
        )
        self.assertRaises(JIRAError, self.jira.remote_link, self.issue_key, _id)

    def test_delete_remote_link_with_invalid_args(self):
        self.assertRaises(ValueError, self.jira.delete_remote_link, self.issue_key)


class WebsudoTests(JiraTestCase):
    def test_kill_websudo(self):
        self.jira.kill_websudo()

    # def test_kill_websudo_without_login_raises(self):
    #    self.assertRaises(ConnectionError, JIRA)


class UserAdministrationTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.test_username = f"test_{self.test_manager.project_a}"
        self.test_email = f"{self.test_username}@example.com"
        self.test_password = rndpassword()
        self.test_groupname = f"testGroupFor_{self.test_manager.project_a}"

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
