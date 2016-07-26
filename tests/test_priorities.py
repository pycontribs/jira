from tests import not_on_custom_jira_instance


def test_priorities(jira_admin):
    priorities = jira_admin.priorities()

    assert len(priorities) == 5


@not_on_custom_jira_instance
def test_priority(jira_admin):
    priority = jira_admin.priority('2')

    assert priority.id == '2'
    assert priority.name == 'Critical'
