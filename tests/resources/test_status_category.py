from tests.conftest import JiraTestCase


class StatusCategoryTests(JiraTestCase):
    def test_statuscategories(self):
        found = False
        statuscategories = self.jira.statuscategories()
        for statuscategory in statuscategories:
            if statuscategory.id == 1 and statuscategory.name == u"No Category":
                found = True
                break
        self.assertTrue(
            found, "StatusCategory with id=1 not found. [%s]" % statuscategories
        )
        self.assertGreater(len(statuscategories), 0)

    def test_statuscategory(self):
        statuscategory = self.jira.statuscategory(1)
        self.assertEqual(statuscategory.id, 1)
        self.assertEqual(statuscategory.name, "No Category")
