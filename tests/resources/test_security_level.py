from tests.conftest import JiraTestCase, broken_test


@broken_test(
    reason="Skipped due to standalone jira docker image has no security schema created by default"
)
class SecurityLevelTests(JiraTestCase):
    def test_security_level(self):
        # This is hardcoded due to Atlassian bug: https://jira.atlassian.com/browse/JRA-59619
        sec_level = self.jira.security_level("10000")
        self.assertEqual(sec_level.id, "10000")
