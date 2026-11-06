from __future__ import annotations

import pytest

import jira.client
from jira.client import TEXT_FIELD_MAX_LENGTH
from jira.resources import CommentProperty
from tests.conftest import JiraTestCase, allow_on_cloud


class CommentTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1_key = self.test_manager.project_b_issue1
        self.issue_2_key = self.test_manager.project_b_issue2
        self.issue_3_key = self.test_manager.project_b_issue3

    def tearDown(self) -> None:
        for issue in [self.issue_1_key, self.issue_2_key, self.issue_3_key]:
            for comment in self.jira.comments(issue):
                comment.delete()

    @allow_on_cloud
    def test_comments(self):
        for issue in [self.issue_1_key, self.jira.issue(self.issue_2_key)]:
            self.jira.issue(issue)
            comment1 = self.jira.add_comment(issue, "First comment")
            comment2 = self.jira.add_comment(issue, "Second comment")
            comments = self.jira.comments(issue)
            assert comments[0].body == "First comment"
            assert comments[1].body == "Second comment"
            comment1.delete()
            comment2.delete()
            comments = self.jira.comments(issue)
            assert len(comments) == 0

    @allow_on_cloud
    def test_comments_start_at(self):
        comments_created = []
        for i in range(10):
            comments_created.append(
                self.jira.add_comment(self.issue_1_key, f"Comment #{i + 1}")
            )
        comments = self.jira.comments(self.issue_1_key, start_at=5)
        self.assertEqual(len(comments), 5)
        self.assertEqual(comments[0].body, "Comment #6")
        for comment in comments_created:
            comment.delete()
        comments = self.jira.comments(self.issue_1_key)
        assert len(comments) == 0

    @allow_on_cloud
    def test_comments_max_results(self):
        comments_created = []
        for i in range(10):
            comments_created.append(
                self.jira.add_comment(self.issue_1_key, f"Comment #{i + 1}")
            )
        comments = self.jira.comments(self.issue_1_key, max_results=4)
        self.assertEqual(len(comments), 4)
        self.assertEqual(comments[0].body, "Comment #1")
        for comment in comments_created:
            comment.delete()
        comments = self.jira.comments(self.issue_1_key)
        assert len(comments) == 0

    @allow_on_cloud
    def test_comments_order_by(self):
        comments_created = []
        for i in range(10):
            comments_created.append(
                self.jira.add_comment(self.issue_1_key, f"Comment #{i + 1}")
            )
        comments = self.jira.comments(self.issue_1_key, order_by="created")
        self.assertEqual(comments[0].body, "Comment #1")
        comments = self.jira.comments(self.issue_1_key, order_by="+created")
        self.assertEqual(comments[0].body, "Comment #1")
        comments = self.jira.comments(self.issue_1_key, order_by="-created")
        self.assertEqual(comments[0].body, "Comment #10")
        for comment in comments_created:
            comment.delete()
        comments = self.jira.comments(self.issue_1_key)
        assert len(comments) == 0

    @allow_on_cloud
    def test_expanded_comments(self):
        comment1 = self.jira.add_comment(self.issue_1_key, "First comment")
        comment2 = self.jira.add_comment(self.issue_1_key, "Second comment")
        comments = self.jira.comments(self.issue_1_key, expand="renderedBody")
        self.assertTrue(hasattr(comments[0], "renderedBody"))
        ret_comment1 = self.jira.comment(
            self.issue_1_key, comment1.id, expand="renderedBody"
        )
        ret_comment2 = self.jira.comment(self.issue_1_key, comment2.id)
        comment1.delete()
        comment2.delete()
        self.assertTrue(hasattr(ret_comment1, "renderedBody"))
        self.assertFalse(hasattr(ret_comment2, "renderedBody"))
        comments = self.jira.comments(self.issue_1_key)
        assert len(comments) == 0

    @allow_on_cloud
    def test_add_comment(self):
        comment = self.jira.add_comment(
            self.issue_3_key,
            "a test comment!",
            visibility={"type": "role", "value": "Administrators"},
        )
        self.assertEqual(comment.body, "a test comment!")
        self.assertEqual(comment.visibility.type, "role")
        self.assertEqual(comment.visibility.value, "Administrators")
        comment.delete()

    @allow_on_cloud
    def test_add_comment_with_issue_obj(self):
        issue = self.jira.issue(self.issue_3_key)
        comment = self.jira.add_comment(
            issue,
            "a new test comment!",
            visibility={"type": "role", "value": "Administrators"},
        )
        self.assertEqual(comment.body, "a new test comment!")
        self.assertEqual(comment.visibility.type, "role")
        self.assertEqual(comment.visibility.value, "Administrators")
        comment.delete()

    @allow_on_cloud
    def test_update_comment(self):
        comment = self.jira.add_comment(self.issue_3_key, "updating soon!")
        comment.update(body="updated!")
        assert comment.body == "updated!"
        # self.assertEqual(comment.visibility.type, 'role')
        # self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    @allow_on_cloud
    def test_update_comment_with_notify(self):
        comment = self.jira.add_comment(self.issue_3_key, "updating soon!")
        comment.update(body="updated! without notification", notify=False)
        assert comment.body == "updated! without notification"
        comment.delete()

    def test_comment_property(self):
        comment = self.jira.add_comment(self.issue_1_key, "comment for property test")
        comment_prop_data = {"internal": "true"}
        self.jira.add_comment_property(comment, "sd.public.comment", comment_prop_data)
        comment_prop = self.jira.comment_property(comment, "sd.public.comment")
        assert isinstance(comment_prop, CommentProperty)
        assert comment_prop.value.internal.lower() == "true"
        comment.delete()


@pytest.mark.unit
class TestCommentOffline:
    def test_comment_property_roundtrip(self, requests_mock):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        url = "https://jira.example.com/rest/api/2/comment/10500/properties"
        prop = {"key": "sd.public.comment", "value": {"internal": True}}
        requests_mock.put(f"{url}/sd.public.comment", status_code=204)
        requests_mock.get(f"{url}/sd.public.comment", json=prop)
        requests_mock.get(url, json={"keys": [{"key": "sd.public.comment"}]})

        client.add_comment_property("10500", "sd.public.comment", {"internal": True})
        single = client.comment_property("10500", "sd.public.comment")
        listed = client.comment_properties("10500")

        put = next(r for r in requests_mock.request_history if r.method == "PUT")
        assert put.json() == {"internal": True}
        assert isinstance(single, jira.resources.CommentProperty)
        assert single.value.internal is True
        assert single.self == f"{url}/sd.public.comment"
        assert [p.key for p in listed] == ["sd.public.comment"]

    def test_add_comment_rejects_body_over_limit(self, offline_jira, requests_mock):
        body = "a" * (TEXT_FIELD_MAX_LENGTH + 1)

        with pytest.raises(ValueError, match="body"):
            offline_jira.add_comment("KEY-1", body)

        assert requests_mock.request_history == []

    def test_add_comment_accepts_body_at_limit(self, offline_jira, requests_mock):
        body = "a" * TEXT_FIELD_MAX_LENGTH
        requests_mock.post(
            "https://jira.atlassian.com/rest/api/2/issue/KEY-1/comment",
            json={"id": "1", "body": body},
        )

        comment = offline_jira.add_comment("KEY-1", body)

        assert comment.body == body
