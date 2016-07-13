def test_statuses(jira_admin):
    found = False
    statuses = jira_admin.statuses()
    for status in statuses:
        if status.id == '10001' and status.name == 'Done':
            found = True
            break
    assert found, "Status Open with id=1 not found. [%s]" % statuses


def test_status(jira_admin):
    status = jira_admin.status('10001')

    assert status.id == '10001'
    assert status.name == 'Done'
