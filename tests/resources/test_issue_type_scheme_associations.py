from __future__ import annotations

from tests.conftest import JiraTestCase


class IssueTypeSchemeAssociationTests(JiraTestCase):
    def test_scheme_associations(self):
        all_schemes = self.jira.issue_type_schemes()
        # there should be more than 1 scheme
        self.assertGreaterEqual(len(all_schemes), 2)
        test_pass = False
        for scheme in all_schemes:
            associations = self.jira.get_issue_type_scheme_associations(scheme["id"])
            # As long as one of these schemes is associated with a project-like object
            # we're probably ok.
            if len(associations) > 0:
                self.assertTrue(associations[0].get("id", False))
                self.assertTrue(associations[0].get("key", False))
                self.assertTrue(associations[0].get("lead", False))
                test_pass = True
                break
        self.assertTrue(test_pass)
