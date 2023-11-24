from __future__ import annotations

from tests.conftest import jira_svcTestCase


class StatusCategoryTests(jira_svcTestCase):
    def test_statuscategories(self):
        found = False
        statuscategories = self.jira_svc.statuscategories()
        for statuscategory in statuscategories:
            if statuscategory.id == 1 and statuscategory.name == "No Category":
                found = True
                break
        self.assertTrue(
            found, f"StatusCategory with id=1 not found. [{statuscategories}]"
        )
        self.assertGreater(len(statuscategories), 0)

    def test_statuscategory(self):
        statuscategory = self.jira_svc.statuscategory(1)
        self.assertEqual(statuscategory.id, 1)
        self.assertEqual(statuscategory.name, "No Category")
