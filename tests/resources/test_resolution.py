from tests.conftest import JiraTestCase


class ResolutionTests(JiraTestCase):
    def test_resolutions(self):
        resolutions = self.jira.resolutions()
        self.assertGreaterEqual(len(resolutions), 1)

    def test_resolution(self):
        resolution = self.jira.resolution("10002")
        self.assertEqual(resolution.id, "10002")
        self.assertEqual(resolution.name, "Duplicate")
