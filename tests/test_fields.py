from tests import not_on_custom_jira_instance


@not_on_custom_jira_instance
def test_fields(jira_admin):
    fields = jira_admin.fields()
    assert len(fields) > 10
