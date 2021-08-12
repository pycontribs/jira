from tests.conftest import JiraTestCase


class StatusTests(JiraTestCase):
    def test_statuses(self):
        found = False
        statuses = self.jira.statuses()
        for status in statuses:
            if status.name == "Done":
                found = True
                # find status
                s = self.jira.status(status.id)
                self.assertEqual(s.id, status.id)
                break
        self.assertTrue(found, "Status Done not found. [%s]" % statuses)
        self.assertGreater(len(statuses), 0)
