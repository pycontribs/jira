from __future__ import annotations

from contextlib import contextmanager

from tests.conftest import JiraTestCase, allow_on_cloud, rndstr


class FilterTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

        self.filter_jql: str = f"project = {self.project_b} AND component is not EMPTY"
        self.filter_name: str = "some filter " + rndstr()
        self.filter_desc: str = "just some new test filter"
        self.filter_favourite: bool | None = False

    @contextmanager
    def make_filter(self, **kwargs):
        try:
            new_filter = self.jira.create_filter(
                name=kwargs.pop("name", self.filter_name),
                description=kwargs.pop("description", self.filter_desc),
                jql=kwargs.pop("jql", self.filter_jql),
                favourite=kwargs.pop("favourite", self.filter_favourite),
                share_permissions=kwargs.pop("share_permissions", None),
            )
            if len(kwargs):
                raise ValueError("Incorrect kwarg used !")
            yield new_filter
        finally:
            new_filter.delete()

    @allow_on_cloud
    def test_filter(self):
        with self.make_filter() as myfilter:
            self.assertEqual(myfilter.name, self.filter_name)
            if self.is_jira_cloud_ci:
                self.assertEqual(
                    myfilter.owner.accountId, self.jira.myself()["accountId"]
                )
            else:
                self.assertEqual(myfilter.owner.name, self.test_manager.user_admin.name)

    def test_create_filter_with_share_permissions(self):
        project_id = self.jira.project(self.project_b).id
        shares = [
            {"type": "group", "groupname": "jira-administrators"},
            {"type": "project", "projectId": project_id},
        ]

        with self.make_filter(share_permissions=shares) as myfilter:
            shared_with = {
                (p["type"], p.get("group", {}).get("name") or p["project"]["id"])
                for p in myfilter.raw["sharePermissions"]
            }

        self.assertEqual(
            shared_with, {("group", "jira-administrators"), ("project", project_id)}
        )

    @allow_on_cloud
    def test_favourite_filters(self):
        filter_name = f"filter-to-fav-{self.filter_name}"
        with self.make_filter(name=filter_name, favourite=True):
            new_filters = self.jira.favourite_filters()
            assert filter_name in [f.name for f in new_filters]

    @allow_on_cloud
    def test_filter_update_empty_description(self):
        new_jql = f"{self.filter_jql} ORDER BY created ASC"
        new_name = f"new_{self.filter_name}"
        with self.make_filter(description=None) as myfilter:
            self.jira.update_filter(
                myfilter.id,
                name=new_name,
                description=None,
                jql=new_jql,
                favourite=None,
            )
            updated_filter = self.jira.filter(myfilter.id)
            assert updated_filter.name == new_name
            assert updated_filter.jql == new_jql
            assert not hasattr(updated_filter, "description")

    @allow_on_cloud
    def test_filter_update_empty_description_with_new_description(self):
        new_desc = "new description"
        with self.make_filter(description=None) as myfilter:
            self.jira.update_filter(
                myfilter.id,
                name=myfilter.name,
                description=new_desc,
                jql=myfilter.jql,
                favourite=None,
            )
            updated_filter = self.jira.filter(myfilter.id)
            assert updated_filter.description == new_desc
