def test_server_info(jira_admin):
    server_info = jira_admin.server_info()

    assert 'baseUrl' in server_info
    assert 'version' in server_info
