from __future__ import annotations

from tests.conftest import JiraTestCase


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

    def test_update_comment(self):
        comment = self.jira.add_comment(self.issue_3_key, "updating soon!")
        comment.update(body="updated!")
        assert comment.body == "updated!"
        # self.assertEqual(comment.visibility.type, 'role')
        # self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_update_comment_with_notify(self):
        comment = self.jira.add_comment(self.issue_3_key, "updating soon!")
        comment.update(body="updated! without notification", notify=False)
        assert comment.body == "updated! without notification"
        comment.delete()
