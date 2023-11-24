from __future__ import annotations

from tests.conftest import jira_svcTestCase


class WatchersTests(jira_svcTestCase):
    def setUp(self):
        jira_svcTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1

    def test_add_remove_watcher(self):
        # removing it in case it exists, so we know its state
        self.jira_svc.remove_watcher(self.issue_1, self.test_manager.user_normal.name)
        init_watchers = self.jira_svc.watchers(self.issue_1).watchCount

        # adding a new watcher
        self.jira_svc.add_watcher(self.issue_1, self.test_manager.user_normal.name)
        self.assertEqual(self.jira_svc.watchers(self.issue_1).watchCount, init_watchers + 1)

        # now we verify that remove does indeed remove watchers
        self.jira_svc.remove_watcher(self.issue_1, self.test_manager.user_normal.name)
        new_watchers = self.jira_svc.watchers(self.issue_1).watchCount
        self.assertEqual(init_watchers, new_watchers)
