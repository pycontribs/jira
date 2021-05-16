from tests.conftest import JiraTestCase, not_on_custom_jira_instance


class CustomFieldOptionTests(JiraTestCase):
    @not_on_custom_jira_instance
    def test_custom_field_option(self):
        option = self.jira.custom_field_option("10001")
        self.assertEqual(option.value, "To Do")
