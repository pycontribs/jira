from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

import jira.client
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

    def test_attach_with_no_filename(self):
        issue = self.jira.issue(self.issue_1)
        attachment_no_filename_specified = self.jira.add_attachment(
            issue=issue.key, attachment=TEST_ATTACH_PATH, filename=None
        )
        new_attachment = self.jira.attachment(attachment_no_filename_specified.id)
        msg = f"attachment, no filename specified {new_attachment.__dict__} of issue {issue}"
        assert new_attachment.filename == Path(TEST_ATTACH_PATH).name, msg

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


def test_add_attachment_accepts_bytes(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    content = b"example content"
    bodies: list[bytes] = []

    def respond(request, context):
        bodies.append(request.body.read())
        return [{"id": "10001", "filename": "example.txt", "size": len(content)}]

    requests_mock.post(
        "https://jira.example.com/rest/api/2/issue/QQ-1/attachments", json=respond
    )

    attachment = client.add_attachment("QQ-1", content, "example.txt")

    assert attachment.size == len(content)
    assert b'filename="example.txt"' in bodies[0]
    assert content in bodies[0]
    assert requests_mock.last_request.headers["X-Atlassian-Token"] == "no-check"


def test_add_attachment_stream_uses_its_name(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    bodies: list[bytes] = []

    def respond(request, context):
        bodies.append(request.body.read())
        return [{"id": "10001", "filename": "report.txt", "size": 7}]

    requests_mock.post(
        "https://jira.example.com/rest/api/2/issue/QQ-1/attachments", json=respond
    )
    stream = io.BytesIO(b"content")
    stream.name = "reports/report.txt"

    client.add_attachment("QQ-1", stream)

    assert b'filename="report.txt"' in bodies[0]


def test_add_attachment_stream_without_name_raises(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )

    with pytest.raises(ValueError, match="filename is required"):
        client.add_attachment("QQ-1", io.BytesIO(b"content"))

    assert not requests_mock.called


def test_add_attachment_bytes_without_filename_raises(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )

    with pytest.raises(ValueError, match="filename is required"):
        client.add_attachment("QQ-1", b"example content")

    assert not requests_mock.called
