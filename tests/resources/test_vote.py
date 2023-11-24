from __future__ import annotations

from tests.conftest import jira_svcTestCase


class VoteTests(jira_svcTestCase):
    def setUp(self):
        jira_svcTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1

    def test_votes(self):
        self.jira_svc_normal.remove_vote(self.issue_1)
        # not checking the result on this
        votes = self.jira_svc.votes(self.issue_1)
        self.assertEqual(votes.votes, 0)

        self.jira_svc_normal.add_vote(self.issue_1)
        new_votes = self.jira_svc.votes(self.issue_1)
        assert votes.votes + 1 == new_votes.votes

        self.jira_svc_normal.remove_vote(self.issue_1)
        new_votes = self.jira_svc.votes(self.issue_1)
        assert votes.votes == new_votes.votes

    def test_votes_with_issue_obj(self):
        issue = self.jira_svc_normal.issue(self.issue_1)
        self.jira_svc_normal.remove_vote(issue)
        # not checking the result on this
        votes = self.jira_svc.votes(issue)
        self.assertEqual(votes.votes, 0)

        self.jira_svc_normal.add_vote(issue)
        new_votes = self.jira_svc.votes(issue)
        assert votes.votes + 1 == new_votes.votes

        self.jira_svc_normal.remove_vote(issue)
        new_votes = self.jira_svc.votes(issue)
        assert votes.votes == new_votes.votes
