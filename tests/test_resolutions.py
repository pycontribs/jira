from tests import not_on_custom_jira_instance


@not_on_custom_jira_instance
def test_resolutions(jira_admin):
    resolutions = jira_admin.resolutions()
    assert len(resolutions) >= 1


@not_on_custom_jira_instance
def test_resolution(jira_admin):
    resolution = jira_admin.resolution('2')

    assert resolution.id == '2'
    assert resolution.name == 'Won\'t Fix'
