from __future__ import annotations

from contextlib import contextmanager

import pytest

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


def test_add_filter_share_permission_posts_one_permission_per_request(
    offline_jira, requests_mock
):
    offline_jira._version = (8, 20, 0)
    url = "https://jira.atlassian.com/rest/api/latest/filter/10000/permission"
    group = {"type": "group", "groupname": "jira-users"}
    project = {"type": "project", "projectId": "10100"}
    requests_mock.post(
        url,
        [
            {"json": [{"id": 1, **group}]},
            {"json": [{"id": 1, **group}, {"id": 2, **project}]},
        ],
    )

    result = offline_jira.add_filter_share_permission("10000", [group, project])

    assert [r.json() for r in requests_mock.request_history] == [group, project]
    assert result == [{"id": 1, **group}, {"id": 2, **project}]


def test_add_filter_share_permission_wraps_a_single_permission(
    offline_jira, requests_mock
):
    offline_jira._version = (8, 20, 0)
    group = {"type": "group", "groupname": "jira-users"}
    requests_mock.post(
        "https://jira.atlassian.com/rest/api/latest/filter/10000/permission",
        json={"id": 1, **group},
    )

    result = offline_jira.add_filter_share_permission(10000, group)

    assert result == [{"id": 1, **group}]


@pytest.mark.parametrize(
    "call",
    [
        lambda j: j.add_filter_share_permission("10000", {"type": "global"}),
        lambda j: j.create_filter(name="f", share_permissions={"type": "global"}),
    ],
    ids=["add_filter_share_permission", "create_filter"],
)
def test_filter_share_permission_on_old_server_raises_before_sending(
    offline_jira, requests_mock, call
):
    offline_jira._version = (7, 0, 10)

    with pytest.raises(NotImplementedError, match="needs Jira 7.1 or later"):
        call(offline_jira)
    assert requests_mock.call_count == 0


def test_create_filter_returns_filter_with_added_share_permissions(
    offline_jira, requests_mock
):
    offline_jira._version = (8, 20, 0)
    base = "https://jira.atlassian.com/rest/api/2/filter"
    requests_mock.post(base, json={"id": "10000", "self": f"{base}/10000"})
    requests_mock.post(
        "https://jira.atlassian.com/rest/api/latest/filter/10000/permission",
        json=[{"id": 1, "type": "global"}],
    )
    requests_mock.get(
        f"{base}/10000",
        json={
            "id": "10000",
            "self": f"{base}/10000",
            "sharePermissions": [{"id": 1, "type": "global"}],
        },
    )

    created = offline_jira.create_filter(name="f", share_permissions={"type": "global"})

    permission_post = requests_mock.request_history[1]
    assert permission_post.url.endswith("/latest/filter/10000/permission")
    assert permission_post.json() == {"type": "global"}
    assert created.raw["sharePermissions"] == [{"id": 1, "type": "global"}]
