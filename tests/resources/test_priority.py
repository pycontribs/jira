from tests.conftest import JiraTestCase


class PrioritiesTests(JiraTestCase):
    def test_priorities(self):
        priorities = self.jira.priorities()
        self.assertEqual(len(priorities), 5)

    def test_priority(self):
        priority = self.jira.priority("2")
        self.assertEqual(priority.id, "2")
        self.assertEqual(priority.name, "High")
