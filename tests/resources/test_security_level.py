from __future__ import annotations

import jira.client
from jira.resources import SecurityLevel
from tests.conftest import JiraTestCase, broken_test


@broken_test(
    reason="Skipped due to standalone jira docker image has no security schema created by default"
)
class SecurityLevelTests(JiraTestCase):
    def test_security_level(self):
        # This is hardcoded due to Atlassian bug: https://jira.atlassian.com/browse/JRA-59619
        sec_level = self.jira.security_level("10000")
        self.assertEqual(sec_level.id, "10000")


def test_project_securitylevels(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.get(
        "https://jira.example.com/rest/api/2/project/ABC/securitylevel",
        json={
            "levels": [
                {"id": "10000", "name": "Internal", "description": "Staff only"},
                {"id": "10001", "name": "Public", "description": "Everyone"},
            ]
        },
    )

    levels = client.project_securitylevels("ABC")

    assert [level.name for level in levels] == ["Internal", "Public"]
    assert all(isinstance(level, SecurityLevel) for level in levels)
