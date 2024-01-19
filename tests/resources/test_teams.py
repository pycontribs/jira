from __future__ import annotations

import os
from contextlib import contextmanager

from tests.conftest import JiraTestCase, allow_on_cloud


@allow_on_cloud
class TeamsTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.test_team_name = f"testTeamFor_{self.test_manager.project_a}"
        self.test_team_type = "OPEN"
        self.org_id = os.environ["CI_JIRA_ORG_ID"]
        self.test_team_description = "test Description"

    @contextmanager
    def make_team(self, **kwargs):
        try:
            new_team = self.jira.create_team(
                self.org_id,
                self.test_team_description,
                self.test_team_name,
                self.test_team_type,
            )

            if len(kwargs):
                raise ValueError("Incorrect kwarg used !")
            yield new_team
        finally:
            new_team.delete()

    def test_team_creation(self):
        with self.make_team() as test_team:
            self.assertEqual(
                self.test_team_name,
                test_team["displayName"],
            )
            self.assertEqual(self.test_team_description, test_team["description"])
            self.assertEqual(self.test_team_type, test_team["teamType"])

    def test_team_get(self):
        with self.make_team() as test_team:
            fetched_team = self.jira.get_team(self.org_id, test_team.id)
            self.assertEqual(
                self.test_team_name,
                fetched_team["displayName"],
            )

    def test_team_deletion(self):
        with self.make_team() as test_team:
            ok = self.jira.remove_team(self.org_id, test_team.id)
            self.assertTrue(ok)

    def test_updating_team(self):
        new_desc = "Fake new description"
        new_name = "Fake new Name"
        with self.make_team() as test_team:
            updated_team = self.jira.update_team(
                self.org_id, test_team.id, description=new_desc, displayName=new_name
            )
            self.assertEqual(new_name, updated_team["displayName"])
            self.assertEqual(new_desc, updated_team["description"])

    def test_adding_team_members(self):
        with self.make_team() as test_team:
            self.jira.add_team_members(
                self.org_id, test_team.id, members=[self.user_admin["accountId"]]
            )

    def test_get_team_members(self):
        expected_accounts_id = [self.user_admin["accountId"]]
        with self.make_team() as test_team:
            self.jira.add_team_members(
                self.org_id, test_team.id, members=expected_accounts_id
            )

            fetched_account_ids = self.jira.team_members(self.org_id, test_team.id)
            self.assertEqual(expected_accounts_id, fetched_account_ids)
