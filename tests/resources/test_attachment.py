import os

from tests.conftest import TEST_ATTACH_PATH, JiraTestCase


class AttachmentTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.attachment = None

    def test_0_attachment_meta(self):
        meta = self.jira.attachment_meta()
        self.assertTrue(meta["enabled"])
        # we have no control over server side upload limit
        self.assertIn("uploadLimit", meta)

    def test_1_add_remove_attachment_using_filestream(self):
        issue = self.jira.issue(self.issue_1)
        with open(TEST_ATTACH_PATH, "rb") as f:
            attachment = self.jira.add_attachment(issue, f, "new test attachment")
            new_attachment = self.jira.attachment(attachment.id)
            msg = f"attachment {new_attachment.__dict__} of issue {issue}"
            self.assertEqual(new_attachment.filename, "new test attachment", msg=msg)
            self.assertEqual(
                new_attachment.size, os.path.getsize(TEST_ATTACH_PATH), msg=msg
            )
            # JIRA returns a HTTP 204 upon successful deletion
            self.assertEqual(attachment.delete().status_code, 204)

    def test_2_add_remove_attachment_using_filename(self):
        issue = self.jira.issue(self.issue_1)
        attachment = self.jira.add_attachment(
            issue, TEST_ATTACH_PATH, "new test attachment"
        )
        new_attachment = self.jira.attachment(attachment.id)
        msg = f"attachment {new_attachment.__dict__} of issue {issue}"
        self.assertEqual(new_attachment.filename, "new test attachment", msg=msg)
        self.assertEqual(
            new_attachment.size, os.path.getsize(TEST_ATTACH_PATH), msg=msg
        )
        # JIRA returns a HTTP 204 upon successful deletion
        self.assertEqual(attachment.delete().status_code, 204)
