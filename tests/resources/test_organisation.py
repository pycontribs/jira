from __future__ import annotations

from contextlib import contextmanager

from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class TeamsTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.test_org_name = "testOrg"

    @contextmanager
    def make_org(self):
        try:
            new_org = self.jira.create_org(self.test_org_name)
            yield new_org
        finally:
            new_org.delete()

    def test_org_creation(self):
        with self.make_org() as test_org:
            self.assertEqual(self.test_org_name, test_org["name"])

    def test_org_deletion(self):
        with self.make_org() as test_org:
            ok = self.jira.remove_org(test_org.id)
            self.assertTrue(ok)

    def test_fetch_one_org(self):
        with self.make_org() as test_org:
            found_org = self.jira.org(test_org.id)
            self.assertEqual(test_org["name"], found_org["name"])

    def test_fetch_multiple_orgs(self):
        expected_org_was_found = False
        with self.make_org() as test_org:
            found_orgs = self.jira.orgs()
            self.assertGreater(len(found_orgs), 0)
            for org in found_orgs:
                if org["name"] == test_org["name"]:
                    expected_org_was_found = True
            self.assertTrue(expected_org_was_found)

    def test_add_users_to_org(self):
        users_to_add = [self.user_admin.id]
        with self.make_org() as test_org:
            ok = self.jira.add_users_to_org(test_org.id, users_to_add)
            self.assertTrue(ok)

    def test_get_users_in_org(self):
        users_to_add = [self.user_admin.id]
        with self.make_org() as test_org:
            ok = self.jira.add_users_to_org(test_org.id, users_to_add)
            self.assertTrue(ok)
            found_users = self.jira.org_users(test_org.id)
            self.assertIn(self.user_admin.id, found_users)

    def test_remove_user_from_org(self):
        users_to_add = [self.user_admin.id]
        with self.make_org() as test_org:
            ok = self.jira.add_users_to_org(test_org.id, users_to_add)
            self.assertTrue(ok)
            found_users = self.jira.org_users(test_org.id)
            self.assertIn(self.user_admin.id, found_users)
            removal_ok = self.jira.remove_users_from_org(test_org.id, users_to_add)
            self.assertTrue(removal_ok)
            found_users_after_removal = self.jira.org_users(test_org.id)
            self.assertNotIn(self.user_admin.id, found_users_after_removal)
