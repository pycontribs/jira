from tests.conftest import JiraTestCase


class CustomFieldOptionTests(JiraTestCase):
    def test_custom_field_option(self):
        option = self.jira.custom_field_option("10000")
        self.assertEqual(option.value, "To Do")
