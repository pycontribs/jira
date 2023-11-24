from __future__ import annotations

from tests.conftest import jira_svcTestCase


class StatusTests(jira_svcTestCase):
    def test_statuses(self):
        found = False
        statuses = self.jira_svc.statuses()
        for status in statuses:
            if status.name == "Done":
                found = True
                # find status
                s = self.jira_svc.status(status.id)
                self.assertEqual(s.id, status.id)
                break
        self.assertTrue(found, f"Status Done not found. [{statuses}]")
        self.assertGreater(len(statuses), 0)
