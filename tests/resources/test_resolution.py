from __future__ import annotations

from tests.conftest import jira_svcTestCase


class ResolutionTests(jira_svcTestCase):
    def test_resolutions(self):
        resolutions = self.jira_svc.resolutions()
        self.assertGreaterEqual(len(resolutions), 1)

    def test_resolution(self):
        resolution = self.jira_svc.resolution("10002")
        self.assertEqual(resolution.id, "10002")
        self.assertEqual(resolution.name, "Duplicate")
