from __future__ import annotations

from tests.conftest import jira_svcTestCase, broken_test


@broken_test(
    reason="Skipped due to standalone jira_svc docker image has no security schema created by default"
)
class SecurityLevelTests(jira_svcTestCase):
    def test_security_level(self):
        # This is hardcoded due to Atlassian bug: https://jira_svc.atlassian.com/browse/JRA-59619
        sec_level = self.jira_svc.security_level("10000")
        self.assertEqual(sec_level.id, "10000")
