import os
from tests import TEST_ATTACH_PATH


def test_attachment_meta(jira_admin):
    meta = jira_admin.attachment_meta()

    assert meta['enabled'] is True
    assert int(meta['uploadLimit']) == 10485760


def test_add_remove_attachment(test_manager, jira_admin):
    issue = jira_admin.issue(test_manager.project_b_issue1)
    attachment = jira_admin.add_attachment(
        issue, open(TEST_ATTACH_PATH, 'rb'), "new test attachment")
    new_attachment = jira_admin.attachment(attachment.id)
    msg = "attachment %s of issue %s" % (new_attachment.__dict__, issue)
    assert new_attachment.filename == 'new test attachment', msg
    assert new_attachment.size == os.path.getsize(TEST_ATTACH_PATH), msg
    assert attachment.delete() is None
