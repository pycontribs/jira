import os

from tests.conftest import TEST_ICON_PATH, JiraTestCase


class UserTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue = self.test_manager.project_b_issue3

    def test_user(self):
        user = self.jira.user(self.test_manager.user_admin.name)
        self.assertTrue(user.name)
        self.assertRegex(
            user.emailAddress, r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        )

    def test_search_assignable_users_for_projects(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN, "%s,%s" % (self.project_a, self.project_b)
        )
        self.assertGreaterEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.CI_JIRA_ADMIN, usernames)

    def test_search_assignable_users_for_projects_maxresults(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN,
            "%s,%s" % (self.project_a, self.project_b),
            maxResults=1,
        )
        self.assertLessEqual(len(users), 1)

    def test_search_assignable_users_for_projects_startat(self):
        users = self.jira.search_assignable_users_for_projects(
            self.test_manager.CI_JIRA_ADMIN,
            "%s,%s" % (self.project_a, self.project_b),
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

    def test_search_users(self):
        users = self.jira.search_users(self.test_manager.CI_JIRA_ADMIN)
        self.assertGreaterEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn(self.test_manager.user_admin.name, usernames)

    def test_search_users_maxresults(self):
        users = self.jira.search_users(self.test_manager.CI_JIRA_USER, maxResults=1)
        self.assertGreaterEqual(1, len(users))

    def test_search_allowed_users_for_issue_by_project(self):
        users = self.jira.search_allowed_users_for_issue(
            self.test_manager.CI_JIRA_USER, projectKey=self.project_a
        )
        self.assertGreaterEqual(len(users), 1)

    def test_search_allowed_users_for_issue_by_issue(self):
        users = self.jira.search_allowed_users_for_issue("a", issueKey=self.issue)
        self.assertGreaterEqual(len(users), 1)

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

    def test_add_users_to_set(self):
        users_set = set([self.test_manager.user_admin, self.test_manager.user_admin])
        self.assertEqual(len(users_set), 1)
