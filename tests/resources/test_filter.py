from tests.conftest import JiraTestCase, rndstr


class FilterTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

    def test_filter(self):
        jql = f"project = {self.project_b} and component is not empty"
        name = "same filter " + rndstr()
        myfilter = self.jira.create_filter(
            name=name, description="just some new test filter", jql=jql, favourite=False
        )
        self.assertEqual(myfilter.name, name)
        self.assertEqual(myfilter.owner.name, self.test_manager.user_admin.name)
        myfilter.delete()

    def test_favourite_filters(self):
        # filters = self.jira.favourite_filters()
        jql = f"project = {self.project_b} and component is not empty"
        name = "filter-to-fav-" + rndstr()
        myfilter = self.jira.create_filter(
            name=name, description="just some new test filter", jql=jql, favourite=True
        )
        new_filters = self.jira.favourite_filters()

        assert name in [f.name for f in new_filters]
        myfilter.delete()
