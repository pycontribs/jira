from __future__ import annotations

from tests.conftest import jira_svcTestCase


class PrioritiesTests(jira_svcTestCase):
    def test_priorities(self):
        priorities = self.jira_svc.priorities()
        self.assertEqual(len(priorities), 5)

    def test_priority(self):
        priority = self.jira_svc.priority("2")
        self.assertEqual(priority.id, "2")
        self.assertEqual(priority.name, "High")
