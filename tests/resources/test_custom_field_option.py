from __future__ import annotations

from tests.conftest import jira_svcTestCase


class CustomFieldOptionTests(jira_svcTestCase):
    def test_custom_field_option(self):
        option = self.jira_svc.custom_field_option("10000")
        self.assertEqual(option.value, "To Do")
