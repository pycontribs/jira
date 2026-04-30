from __future__ import annotations

from tests.conftest import JiraTestCase, min_jira_version


class PinnedCommentTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1_key = self.test_manager.project_b_issue1
        self.issue_2_key = self.test_manager.project_b_issue2
        self.issue_3_key = self.test_manager.project_b_issue3

    def tearDown(self) -> None:
        for issue in [self.issue_1_key, self.issue_2_key, self.issue_3_key]:
            for comment in self.jira.comments(issue):
                comment.delete()

    @min_jira_version((9, 0, 0))
    def test_pincomments(self):
        for issue in [self.issue_1_key, self.jira.issue(self.issue_2_key)]:
            self.jira.issue(issue)
            comment1 = self.jira.add_comment(issue, "First comment")
            self.jira.pin_comment(issue, comment1.id, True)
            comment2 = self.jira.add_comment(issue, "Second comment")
            self.jira.pin_comment(issue, comment2.id, True)
            pinned_comments = self.jira.pinned_comments(issue)
            assert pinned_comments[0].comment.body == "First comment"
            assert pinned_comments[1].comment.body == "Second comment"
            self.jira.pin_comment(issue, comment1.id, False)
            pinned_comments = self.jira.pinned_comments(issue)
            assert len(pinned_comments) == 1
            assert pinned_comments[0].comment.body == "Second comment"
            self.jira.pin_comment(issue, comment2.id, False)
            pinned_comments = self.jira.pinned_comments(issue)
            assert len(pinned_comments) == 0
