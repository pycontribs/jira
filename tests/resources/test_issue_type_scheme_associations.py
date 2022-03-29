from tests.conftest import JiraTestCase


class IssueTypeSchemeAssociationTests(JiraTestCase):
    def test_scheme_associations(self):
        allSchemes = self.jira.issue_type_schemes()
        # there should be more than 1 scheme
        self.assertGreaterEqual(len(allSchemes), 2)
        g2g = False
        for scheme in allSchemes:
            associations = self.jira.get_issue_type_scheme_associations(scheme["id"])
            # As long as one of these schemes is associated with a project-like object
            # we're probably ok.
            if len(associations) > 0:
                print(associations[0].get("id"))
                self.assertTrue(associations[0].get("id", False))
                self.assertTrue(associations[0].get("key", False))
                self.assertTrue(associations[0].get("lead", False))
                g2g = True
                break
        self.assertTrue(g2g)
