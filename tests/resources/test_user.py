from __future__ import annotations

import json
import os
import warnings
from unittest import mock

import pytest

import jira.client
from jira.resources import User
from tests.conftest import TEST_ICON_PATH, JiraTestCase, allow_on_cloud


class UserTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue = self.test_manager.project_b_issue3

    @allow_on_cloud
    def test_user(self):
        """Test that a user can be returned and is the right class"""
        # GIVEN: a User
        expected_user = self.test_manager.user_admin
        # WHEN: The user is searched for using its identifying attribute
        user = self.jira.user(getattr(expected_user, self.identifying_user_property))
        # THEN: it is of the right type, and has an email address of the right format
        assert isinstance(user, User)
        self.assertRegex(
            user.emailAddress, r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        )

    def test_search_assignable_users_for_projects(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN,
            f"{self.project_a},{self.project_b}",
        )
        self.assertGreaterEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    def test_search_assignable_users_for_projects_maxresults(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN,
            f"{self.project_a},{self.project_b}",
            maxResults=1,
        )
        self.assertLessEqual(len(users), 1)

    def test_search_assignable_users_for_projects_startat(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN,
            f"{self.project_a},{self.project_b}",
            startAt=1,
        )
        self.assertGreaterEqual(len(users), 0)

    def test_search_assignable_users_for_issues_by_project(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_ADMIN, project=self.project_b
        )
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    def test_search_assignable_users_for_issues_by_project_maxresults(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_USER, project=self.project_b, maxResults=1
        )
        self.assertLessEqual(len(users), 1)

    def test_search_assignable_users_for_issues_by_project_startat(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_USER, project=self.project_a, startAt=1
        )
        self.assertGreaterEqual(len(users), 0)

    def test_search_assignable_users_for_issues_by_issue(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_ADMIN, issueKey=self.issue
        )
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    def test_search_assignable_users_for_issues_by_issue_maxresults(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_ADMIN, issueKey=self.issue, maxResults=2
        )
        self.assertLessEqual(len(users), 2)

    def test_search_assignable_users_for_issues_by_issue_startat(self):
        users = self.jira.search_assignable_users_for_issues(
            self.test_manager.CI_JIRA_ADMIN, issueKey=self.issue, startAt=2
        )
        self.assertGreaterEqual(len(users), 0)

    def test_user_avatars(self):
        # Tests the end-to-end user avatar creation process: upload as temporary, confirm after cropping,
        # and selection.
        size = os.path.getsize(TEST_ICON_PATH)
        # filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar(
                self.test_manager.CI_JIRA_ADMIN, TEST_ICON_PATH, size, icon.read()
            )
        self.assertIn("cropperOffsetX", props)
        self.assertIn("cropperOffsetY", props)
        self.assertIn("cropperWidth", props)
        self.assertTrue(props["needsCropping"])

        props["needsCropping"] = False
        avatar_props = self.jira.confirm_user_avatar(
            self.test_manager.CI_JIRA_ADMIN, props
        )
        self.assertIn("id", avatar_props)
        self.assertEqual(avatar_props["owner"], self.test_manager.CI_JIRA_ADMIN)

        self.jira.set_user_avatar(self.test_manager.CI_JIRA_ADMIN, avatar_props["id"])

        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertGreaterEqual(
            len(avatars["system"]), 20
        )  # observed values between 20-24 so far
        self.assertGreaterEqual(len(avatars["custom"]), 1)

    def test_set_user_avatar(self):
        def find_selected_avatar(avatars):
            for avatar in avatars["system"]:
                if avatar["isSelected"]:
                    return avatar
            # else:
            #     raise Exception as e
            #     print(e)

        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)

        self.jira.set_user_avatar(
            self.test_manager.CI_JIRA_ADMIN, avatars["system"][0]["id"]
        )
        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(
            find_selected_avatar(avatars)["id"], avatars["system"][0]["id"]
        )

        self.jira.set_user_avatar(
            self.test_manager.CI_JIRA_ADMIN, avatars["system"][1]["id"]
        )
        avatars = self.jira.user_avatars(self.test_manager.CI_JIRA_ADMIN)
        self.assertEqual(
            find_selected_avatar(avatars)["id"], avatars["system"][1]["id"]
        )

    def test_delete_user_avatar(self):
        size = os.path.getsize(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar(
                self.test_manager.CI_JIRA_ADMIN,
                TEST_ICON_PATH,
                size,
                icon.read(),
                auto_confirm=True,
            )
        self.jira.delete_user_avatar(self.test_manager.CI_JIRA_ADMIN, props["id"])

    @allow_on_cloud
    def test_search_users(self):
        # WHEN: the search_users function is called with a requested user
        if self.is_jira_cloud_ci:
            users = self.jira.search_users(query=self.test_manager.CI_JIRA_ADMIN)
        else:
            users = self.jira.search_users(self.test_manager.CI_JIRA_ADMIN)
        # THEN: We get a list of User objects
        self.assertGreaterEqual(len(users), 1)
        self.assertIsInstance(users[0], User)
        #       and the requested user can be found in this list
        user_ids = [getattr(user, self.identifying_user_property) for user in users]
        self.assertIn(
            getattr(self.test_manager.user_admin, self.identifying_user_property),
            user_ids,
        )

    def test_search_users_maxresults(self):
        users = self.jira.search_users(self.test_manager.CI_JIRA_USER, maxResults=1)
        self.assertGreaterEqual(1, len(users))

    @allow_on_cloud
    def test_search_allowed_users_for_issue_by_project(self):
        users = self.jira.search_allowed_users_for_issue(
            self.test_manager.CI_JIRA_USER, projectKey=self.project_a
        )
        self.assertGreaterEqual(len(users), 1)

    @allow_on_cloud
    def test_search_allowed_users_for_issue_by_issue(self):
        users = self.jira.search_allowed_users_for_issue("a", issueKey=self.issue)
        self.assertGreaterEqual(len(users), 1)
        self.assertIsInstance(users[0], User)

    @allow_on_cloud
    def test_search_allowed_users_for_issue_maxresults(self):
        users = self.jira.search_allowed_users_for_issue(
            "a", projectKey=self.project_b, maxResults=2
        )
        self.assertLessEqual(len(users), 2)

    def test_search_allowed_users_for_issue_startat(self):
        users = self.jira.search_allowed_users_for_issue(
            "c", projectKey=self.project_b, startAt=1
        )
        self.assertGreaterEqual(len(users), 0)

    @allow_on_cloud
    def test_add_users_to_set(self):
        users_set = {self.test_manager.user_admin, self.test_manager.user_admin}
        self.assertEqual(len(users_set), 1)


def _user(client: jira.client.JIRA, **raw) -> User:
    return User(client._options, client._session, raw={"self": "x", **raw})


@pytest.mark.unit
class TestUserOffline:
    @pytest.mark.parametrize(
        ("args", "kwargs", "expected_params"),
        [
            (
                ("legacy-user", "PROJ,OPS"),
                {},
                {"username": "legacy-user", "projectKeys": "PROJ,OPS"},
            ),
            (
                (),
                {"accountId": "123:abc", "projectKeys": "PROJ,OPS"},
                {"accountId": "123:abc", "projectKeys": "PROJ,OPS"},
            ),
        ],
        ids=["legacy-positional-username", "cloud-account-id"],
    )
    def test_search_assignable_users_for_projects_parameters(
        self, args, kwargs, expected_params
    ):
        client = jira.client.JIRA(
            server="https://example.atlassian.net",
            get_server_info=False,
            validate=False,
        )
        with mock.patch.object(client, "_fetch_pages", return_value=[]) as fetch_pages:
            result = client.search_assignable_users_for_projects(
                *args, startAt=2, maxResults=7, **kwargs
            )

        assert result == []
        fetch_pages.assert_called_once_with(
            jira.client.User,
            None,
            "user/assignable/multiProjectSearch",
            2,
            7,
            expected_params,
        )

    @pytest.mark.parametrize(
        ("kwargs", "error", "message"),
        [
            ({"accountId": "123:abc"}, TypeError, "projectKeys"),
            ({"projectKeys": "PROJ"}, ValueError, "exactly one"),
            (
                {
                    "username": "legacy-user",
                    "accountId": "123:abc",
                    "projectKeys": "PROJ",
                },
                ValueError,
                "exactly one",
            ),
        ],
    )
    def test_search_assignable_users_for_projects_invalid_arguments(
        self, kwargs, error, message
    ):
        client = jira.client.JIRA(
            server="https://example.atlassian.net",
            get_server_info=False,
            validate=False,
        )
        with mock.patch.object(client, "_fetch_pages") as fetch_pages:
            with pytest.raises(error, match=message):
                client.search_assignable_users_for_projects(**kwargs)
        fetch_pages.assert_not_called()

    @pytest.mark.parametrize(
        "account_id",
        ["5b10ac8d82e05b22cc7d4ef5", "712020:c3eb69e6-897e-4578-a9f5-8d42fd5e948d"],
    )
    def test_get_user_id_keeps_cloud_account_id(self, mock_jira_client, account_id):
        """An account id needs no user search, which requires the Browse users permission."""
        client = mock_jira_client(is_cloud=True)
        with mock.patch.object(jira.client.JIRA, "search_users") as mock_search_users:
            assert client._get_user_id(account_id) == account_id

        mock_search_users.assert_not_called()

    def test_get_user_id_searches_for_other_values(self, mock_jira_client):
        """Cloud hides emailAddress, so a lone account found for an email is the user."""
        client = mock_jira_client(is_cloud=True)
        user = mock.Mock(accountId="5b10ac8d82e05b22cc7d4ef5", emailAddress=None)
        with (
            mock.patch.object(
                jira.client.JIRA, "search_users", return_value=[user]
            ) as mock_search_users,
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("error")
            assert client._get_user_id("user@example.com") == "5b10ac8d82e05b22cc7d4ef5"

        mock_search_users.assert_called_once_with(
            query="user@example.com", maxResults=20
        )

    def test_get_user_id_warns_when_cloud_email_finds_several_accounts(
        self, mock_jira_client
    ):
        client = mock_jira_client(is_cloud=True)
        users = [
            mock.Mock(accountId="5b10ac8d82e05b22cc7d4ef5", emailAddress=None),
            mock.Mock(accountId="5b10ac8d82e05b22cc7d4ef6", emailAddress=None),
        ]
        with (
            mock.patch.object(jira.client.JIRA, "search_users", return_value=users),
            pytest.warns(UserWarning, match="No user with identifier"),
        ):
            assert client._get_user_id("user@example.com") == "5b10ac8d82e05b22cc7d4ef5"

    def test_get_user_id_matches_visible_email(self, mock_jira_client):
        client = mock_jira_client()
        users = [
            mock.Mock(emailAddress="other@example.com"),
            mock.Mock(emailAddress="User@Example.com"),
        ]
        users[0].name, users[1].name = "other", "user"
        with (
            mock.patch.object(jira.client.JIRA, "search_users", return_value=users),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("error")
            assert client._get_user_id("user@example.com") == "user"

    def test_get_user_id_searches_for_account_id_shaped_name_on_server(
        self, mock_jira_client
    ):
        """Self hosted instances identify users by name, so the search is kept."""
        client = mock_jira_client()
        user = mock.Mock(name_="username")
        user.name = "username"
        with (
            mock.patch.object(
                jira.client.JIRA, "search_users", return_value=[user]
            ) as mock_search_users,
            pytest.warns(UserWarning, match="No user with identifier"),
        ):
            assert client._get_user_id("5b10ac8d82e05b22cc7d4ef5") == "username"

        mock_search_users.assert_called_once_with(
            user="5b10ac8d82e05b22cc7d4ef5", maxResults=20
        )

    def test_add_watcher_posts_cloud_account_id_without_user_search(
        self, mock_jira_client
    ):
        """Adding a watcher by account id must not need the Browse users permission."""
        account_id = "5b10ac8d82e05b22cc7d4ef5"
        url = "https://example.atlassian.net/rest/api/2/issue/TEST-1/watchers"
        client = mock_jira_client(is_cloud=True)
        client._session = mock.Mock()
        with (
            mock.patch.object(jira.client.JIRA, "search_users") as mock_search_users,
            mock.patch.object(jira.client.JIRA, "_get_url", return_value=url),
        ):
            client.add_watcher("TEST-1", account_id)

        mock_search_users.assert_not_called()
        client._session.post.assert_called_once_with(url, data=json.dumps(account_id))

    @pytest.mark.parametrize(
        "is_cloud, user_raw, payload",
        [
            (False, {"name": "fred"}, {"name": "fred"}),
            (
                True,
                {"accountId": "5b10ac8d82e05b22cc7d4ef5"},
                {"accountId": "5b10ac8d82e05b22cc7d4ef5"},
            ),
        ],
        ids=["server", "cloud"],
    )
    def test_assign_issue_with_user_object_skips_search(
        self, offline_jira, requests_mock, is_cloud, user_raw, payload
    ):
        if is_cloud:
            offline_jira.deploymentType = "Cloud"
        url = "https://jira.atlassian.com/rest/api/latest/issue/ABC-1/assignee"
        requests_mock.put(url, status_code=204)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            offline_jira.assign_issue("ABC-1", _user(offline_jira, **user_raw))

        assert [r.method for r in requests_mock.request_history] == ["PUT"]
        assert requests_mock.last_request.json() == payload

    def test_watchers_with_user_object_skip_search(self, offline_jira, requests_mock):
        url = "https://jira.atlassian.com/rest/api/2/issue/ABC-1/watchers"
        requests_mock.post(url, status_code=204)
        requests_mock.delete(url, status_code=204)
        user = _user(offline_jira, name="fred")

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            offline_jira.add_watcher("ABC-1", user)
            offline_jira.remove_watcher("ABC-1", user)

        post, delete = requests_mock.request_history
        assert post.json() == "fred"
        assert delete.qs == {"username": ["fred"]}

    @pytest.mark.parametrize(
        "search_results",
        [[{"name": "fred2"}], [{"name": "fred2"}, {"name": "fred3"}]],
        ids=["one result", "several results"],
    )
    def test_user_search_fallback_warns(
        self, offline_jira, requests_mock, search_results
    ):
        requests_mock.get(
            "https://jira.atlassian.com/rest/api/2/user/search",
            json=[{"self": "x", **u} for u in search_results],
        )
        requests_mock.post(
            "https://jira.atlassian.com/rest/api/2/issue/ABC-1/watchers",
            status_code=204,
        )

        with pytest.warns(UserWarning, match="No user with identifier 'fred'"):
            offline_jira.add_watcher("ABC-1", "fred")

        assert requests_mock.last_request.json() == "fred2"

    @pytest.mark.parametrize(
        "search_results",
        [[{"name": "fred"}], [{"name": "fred2"}, {"name": "fred"}]],
        ids=["one result", "several results"],
    )
    def test_user_search_exact_match_does_not_warn(
        self, offline_jira, requests_mock, search_results
    ):
        requests_mock.get(
            "https://jira.atlassian.com/rest/api/2/user/search",
            json=[{"self": "x", **u} for u in search_results],
        )
        requests_mock.post(
            "https://jira.atlassian.com/rest/api/2/issue/ABC-1/watchers",
            status_code=204,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            offline_jira.add_watcher("ABC-1", "fred")

        assert requests_mock.last_request.json() == "fred"
