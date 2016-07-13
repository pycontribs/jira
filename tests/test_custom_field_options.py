from tests import not_on_custom_jira_instance


@not_on_custom_jira_instance
def test_custom_field_option(jira_admin):
    option = jira_admin.custom_field_option('10001')
    assert option.value == 'To Do'
