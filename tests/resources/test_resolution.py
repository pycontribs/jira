from tests.conftest import not_on_custom_jira_instance, JiraTestCase


@not_on_custom_jira_instance
class ResolutionTests(JiraTestCase):
    def test_resolutions(self):
        resolutions = self.jira.resolutions()
        self.assertGreaterEqual(len(resolutions), 1)

    def test_resolution(self):
        resolution = self.jira.resolution("2")
        self.assertEqual(resolution.id, "2")
        self.assertEqual(resolution.name, "Won't Fix")
