from __future__ import annotations

from tests.conftest import JiraTestCase, allow_on_cloud


class CustomFieldOptionTests(JiraTestCase):
    @allow_on_cloud
    def test_custom_field_option(self):
        expected = "Extensive / Widespread"
        if not self.jira._is_cloud:
            expected = "To Do"
        option = self.jira.custom_field_option("10000")
        self.assertEqual(option.value, expected)
