from __future__ import annotations

import logging

import pytest

import jira.client
from jira.exceptions import JIRAError
from jira.resources import Issue
from tests.conftest import (
    JiraTestCase,
    allow_on_cloud,
    find_by_key,
    find_by_key_value,
)

LOGGER = logging.getLogger(__name__)


class IssueTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

    def test_issue(self):
        issue = self.jira.issue(self.issue_1)
        self.assertEqual(issue.key, self.issue_1)
        self.assertEqual(issue.fields.summary, f"issue 1 from {self.project_b}")

    @allow_on_cloud
    def test_issue_search_finds_issue(self):
        issues = self.jira.search_issues(f"key={self.issue_1}")
        self.assertEqual(self.issue_1, issues[0].key)

    @allow_on_cloud
    def test_issue_search_return_type(self):
        issues = self.jira.search_issues(f"key={self.issue_1}")
        self.assertIsInstance(issues, list)
        issues = self.jira.search_issues(f"key={self.issue_1}", json_result=True)
        self.assertIsInstance(issues, dict)

    @allow_on_cloud
    def test_issue_search_only_includes_provided_fields(self):
        issues = self.jira.search_issues(
            f"key={self.issue_1}", fields="comment,assignee"
        )
        self.assertTrue(hasattr(issues[0].fields, "comment"))
        self.assertTrue(hasattr(issues[0].fields, "assignee"))
        self.assertFalse(hasattr(issues[0].fields, "reporter"))

    @allow_on_cloud
    def test_issue_search_default_behaviour_included_fields(self):
        search_str = f"key={self.issue_1}"
        issues = self.jira.search_issues(search_str)
        self.assertTrue(hasattr(issues[0].fields, "reporter"))
        self.assertTrue(hasattr(issues[0].fields, "comment"))

        # fields=None should be valid and return all fields (ie. default behavior)
        self.assertEqual(
            self.jira.search_issues(search_str),
            self.jira.search_issues(search_str, fields=None),
        )

    @allow_on_cloud
    def test_issue_get_field(self):
        issue = self.jira.issue(self.issue_1)
        self.assertEqual(
            issue.fields.description, issue.get_field(field_name="description")
        )

        with self.assertRaisesRegex(AttributeError, ": _something"):
            issue.get_field("_something")

        with self.assertRaisesRegex(AttributeError, "customfield_1234"):
            issue.get_field("customfield_1234")

    @allow_on_cloud
    def test_issue_field_limiting(self):
        issue = self.jira.issue(self.issue_2, fields="summary,comment")
        self.assertEqual(issue.fields.summary, f"issue 2 from {self.project_b}")
        comment1 = self.jira.add_comment(issue, "First comment")
        comment2 = self.jira.add_comment(issue, "Second comment")
        comment3 = self.jira.add_comment(issue, "Third comment")
        self.jira.issue(self.issue_2, fields="summary,comment")
        LOGGER.warning(issue.raw["fields"])
        self.assertFalse(hasattr(issue.fields, "reporter"))
        self.assertFalse(hasattr(issue.fields, "progress"))
        comment1.delete()
        comment2.delete()
        comment3.delete()

    @allow_on_cloud
    def test_issue_fields_by_jql_name(self):
        issue = self.jira.issue(self.issue_1, fields="due")
        raw_fields = issue.raw["fields"]
        self.assertIn("duedate", raw_fields)
        self.assertNotIn("summary", raw_fields)
        self.assertEqual(raw_fields["due"], raw_fields["duedate"])

    @allow_on_cloud
    def test_issue_equal(self):
        issue1 = self.jira.issue(self.issue_1)
        issue2 = self.jira.issue(self.issue_2)
        issues = self.jira.search_issues(f"key={self.issue_1}")
        self.assertTrue(issue1 is not None)
        self.assertTrue(issue1 == issues[0])
        self.assertFalse(issue2 == issues[0])

    @allow_on_cloud
    def test_issue_expand(self):
        issue = self.jira.issue(self.issue_1, expand="editmeta,schema")
        self.assertTrue(hasattr(issue, "editmeta"))
        self.assertTrue(hasattr(issue, "schema"))
        # testing for changelog is not reliable because it may exist or not based on test order
        # self.assertFalse(hasattr(issue, 'changelog'))

    @allow_on_cloud
    def test_create_issue_with_fieldargs(self):
        issue = self.jira.create_issue(
            summary="Test issue created",
            project=self.project_b,
            issuetype={"name": "Bug"},
            description="foo description",
        )  # customfield_10022='XSS'
        self.assertEqual(issue.fields.summary, "Test issue created")
        self.assertEqual(issue.fields.description, "foo description")
        self.assertEqual(issue.fields.issuetype.name, "Bug")
        self.assertEqual(issue.fields.project.key, self.project_b)
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        issue.delete()

    @allow_on_cloud
    def test_create_issue_with_fielddict(self):
        fields = {
            "summary": "Issue created from field dict",
            "project": {"key": self.project_b},
            "issuetype": {"name": "Bug"},
            "description": "Some new issue for test",
            # 'customfield_10022': 'XSS',
            "priority": {"name": "High"},
        }
        issue = self.jira.create_issue(fields=fields)
        self.assertEqual(issue.fields.summary, "Issue created from field dict")
        self.assertEqual(issue.fields.description, "Some new issue for test")
        self.assertEqual(issue.fields.issuetype.name, "Bug")
        self.assertEqual(issue.fields.project.key, self.project_b)
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.priority.name, "High")
        issue.delete()

    @allow_on_cloud
    def test_create_issue_without_prefetch(self):
        issue = self.jira.create_issue(
            summary="Test issue created",
            project=self.project_b,
            issuetype={"name": "Bug"},
            description="some details",
            prefetch=False,
        )  # customfield_10022='XSS'

        assert hasattr(issue, "self")
        assert hasattr(issue, "raw")
        assert "fields" not in issue.raw
        issue.delete()

    @allow_on_cloud
    def test_create_issues(self):
        field_list = [
            {
                "summary": "Issue created via bulk create #1",
                "project": {"key": self.project_b},
                "issuetype": {"name": "Bug"},
                "description": "Some new issue for test",
                # 'customfield_10022': 'XSS',
                "priority": {"name": "High"},
            },
            {
                "summary": "Issue created via bulk create #2",
                "project": {"key": self.project_a},
                "issuetype": {"name": "Bug"},
                "description": "Another new issue for bulk test",
                "priority": {"name": "High"},
            },
        ]
        issues = self.jira.create_issues(field_list=field_list)
        self.assertEqual(len(issues), 2)
        self.assertIsNotNone(issues[0]["issue"], "the first issue has not been created")
        self.assertEqual(
            issues[0]["issue"].fields.summary, "Issue created via bulk create #1"
        )
        self.assertEqual(
            issues[0]["issue"].fields.description, "Some new issue for test"
        )
        self.assertEqual(issues[0]["issue"].fields.issuetype.name, "Bug")
        self.assertEqual(issues[0]["issue"].fields.project.key, self.project_b)
        self.assertEqual(issues[0]["issue"].fields.priority.name, "High")
        self.assertIsNotNone(
            issues[1]["issue"], "the second issue has not been created"
        )
        self.assertEqual(
            issues[1]["issue"].fields.summary, "Issue created via bulk create #2"
        )
        self.assertEqual(
            issues[1]["issue"].fields.description, "Another new issue for bulk test"
        )
        self.assertEqual(issues[1]["issue"].fields.issuetype.name, "Bug")
        self.assertEqual(issues[1]["issue"].fields.project.key, self.project_a)
        self.assertEqual(issues[1]["issue"].fields.priority.name, "High")
        for issue in issues:
            issue["issue"].delete()

    def test_create_issues_one_failure(self):
        field_list = [
            {
                "summary": "Issue created via bulk create #1",
                "project": {"key": self.project_b},
                "issuetype": {"name": "Bug"},
                "description": "Some new issue for test",
                # 'customfield_10022': 'XSS',
                "priority": {"name": "High"},
            },
            {
                "summary": "This issue will not succeed",
                "project": {"key": self.project_a},
                "issuetype": {"name": "InvalidIssueType"},
                "description": "Should not be seen.",
                "priority": {"name": "High"},
            },
            {
                "summary": "However, this one will.",
                "project": {"key": self.project_a},
                "issuetype": {"name": "Bug"},
                "description": "Should be seen.",
                "priority": {"name": "High"},
            },
        ]
        issues = self.jira.create_issues(field_list=field_list)
        self.assertEqual(
            issues[0]["issue"].fields.summary, "Issue created via bulk create #1"
        )
        self.assertEqual(
            issues[0]["issue"].fields.description, "Some new issue for test"
        )
        self.assertEqual(issues[0]["issue"].fields.issuetype.name, "Bug")
        self.assertEqual(issues[0]["issue"].fields.project.key, self.project_b)
        self.assertEqual(issues[0]["issue"].fields.priority.name, "High")
        self.assertEqual(issues[0]["error"], None)
        self.assertEqual(issues[1]["issue"], None)
        self.assertEqual(issues[1]["error"], {"issuetype": "issue type is required"})
        self.assertEqual(issues[1]["input_fields"], field_list[1])
        self.assertEqual(issues[2]["issue"].fields.summary, "However, this one will.")
        self.assertEqual(issues[2]["issue"].fields.description, "Should be seen.")
        self.assertEqual(issues[2]["issue"].fields.issuetype.name, "Bug")
        self.assertEqual(issues[2]["issue"].fields.project.key, self.project_a)
        self.assertEqual(issues[2]["issue"].fields.priority.name, "High")
        self.assertEqual(issues[2]["error"], None)
        self.assertEqual(len(issues), 3)
        for issue in issues:
            if issue["issue"] is not None:
                issue["issue"].delete()

    @allow_on_cloud
    def test_create_issues_without_prefetch(self):
        field_list = [
            dict(
                summary="Test issue #1 created with dicts without prefetch",
                project=self.project_b,
                issuetype={"name": "Bug"},
                description="some details",
            ),
            dict(
                summary="Test issue #2 created with dicts without prefetch",
                project=self.project_a,
                issuetype={"name": "Bug"},
                description="foo description",
            ),
        ]
        issues = self.jira.create_issues(field_list, prefetch=False)

        assert hasattr(issues[0]["issue"], "self")
        assert hasattr(issues[0]["issue"], "raw")
        assert hasattr(issues[1]["issue"], "self")
        assert hasattr(issues[1]["issue"], "raw")
        assert "fields" not in issues[0]["issue"].raw
        assert "fields" not in issues[1]["issue"].raw
        for issue in issues:
            issue["issue"].delete()

    def test_create_issue_with_integer_issuetype(self):
        # take first existing issuetype to avoid problems due to hardcoded name/id later
        issue_types_resolved = self.jira.issue_types()
        dyn_it = issue_types_resolved[0]

        issue = self.jira.create_issue(
            summary="Test issue created using an integer issuetype",
            project=self.project_b,
            issuetype=int(dyn_it.id),
        )
        self.assertEqual(issue.get_field("issuetype").name, dyn_it.name)

    def test_create_issue_with_issue_type_name(self):
        issue_types_resolved = self.jira.issue_types()
        dyn_it = issue_types_resolved[0]

        issue = self.jira.create_issue(
            summary="Test issue created using a str issuetype",
            project=self.project_b,
            issuetype=dyn_it.name,
        )
        self.assertEqual(issue.get_field("issuetype").name, dyn_it.name)

    @allow_on_cloud
    def test_update_with_fieldargs(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating with fieldargs",
            project=self.project_b,
            issuetype={"name": "Bug"},
            description="Will be updated shortly",
        )
        # customfield_10022='XSS')
        issue.update(
            summary="Updated summary",
            description="Now updated",
            issuetype={"name": "Task"},
        )
        self.assertEqual(issue.fields.summary, "Updated summary")
        self.assertEqual(issue.fields.description, "Now updated")
        self.assertEqual(issue.fields.issuetype.name, "Task")
        # self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.project.key, self.project_b)
        issue.delete()

    @allow_on_cloud
    def test_update_with_fielddict(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating with fielddict",
            project=self.project_b,
            description="Will be updated shortly",
            issuetype={"name": "Bug"},
        )
        fields = {
            "summary": "Issue is updated",
            "description": "it sure is",
            "issuetype": {"name": "Task"},
            # 'customfield_10022': 'DOC',
            "priority": {"name": "High"},
        }
        issue.update(fields=fields)
        self.assertEqual(issue.fields.summary, "Issue is updated")
        self.assertEqual(issue.fields.description, "it sure is")
        self.assertEqual(issue.fields.issuetype.name, "Task")
        # self.assertEqual(issue.fields.customfield_10022, 'DOC')
        self.assertEqual(issue.fields.priority.name, "High")
        issue.delete()

    def test_add_remove_field_values(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating labels",
            project=self.project_b,
            description="Label testing",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )

        labelarray = ["testLabel1"]
        fields = {"labels": labelarray}

        issue.update(fields=fields)
        self.assertEqual(issue.fields.labels, ["testLabel1"])

        issue.add_field_value("labels", "testLabel2")
        self.assertEqual(issue.fields.labels, ["testLabel1", "testLabel2"])

        issue.remove_field_value("labels", "testLabel1")
        self.assertEqual(issue.fields.labels, ["testLabel2"])

        issue.delete()

    @allow_on_cloud
    def test_update_with_label(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating labels",
            project=self.project_b,
            description="Label testing",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )

        labelarray = ["testLabel"]
        fields = {"labels": labelarray}

        issue.update(fields=fields)
        self.assertEqual(issue.fields.labels, ["testLabel"])

    def test_update_label_with_proxy(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating labels",
            project=self.project_b,
            description="Label testing",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )

        labelarray = ["testLabel"]
        fields = {"labels": labelarray}
        # This simulates when your Jira server is behind a proxy
        # The self address returned will be different from the configured server
        issue.self = f"https://foo.bar/jira/rest/api/2/issue/{issue.id}"
        issue.update(fields=fields)
        self.assertEqual(issue.fields.labels, ["testLabel"])

    @allow_on_cloud
    def test_update_with_bad_label(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating bad labels",
            project=self.project_b,
            description="Label testing",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )

        issue.fields.labels.append("this should not work")

        fields = {"labels": issue.fields.labels}

        self.assertRaises(JIRAError, issue.update, fields=fields)

    @allow_on_cloud
    def test_update_with_notify_false(self):
        issue = self.jira.create_issue(
            summary="Test issue for updating with notify false",
            project=self.project_b,
            description="Will be updated shortly",
            issuetype={"name": "Bug"},
        )
        issue.update(notify=False, description="Now updated, but silently")
        self.assertEqual(issue.fields.description, "Now updated, but silently")
        issue.delete()

    @allow_on_cloud
    def test_delete(self):
        issue = self.jira.create_issue(
            summary="Test issue created",
            project=self.project_b,
            description="Not long for this world",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )
        key = issue.key
        issue.delete()
        self.assertRaises(JIRAError, self.jira.issue, key)

    def test_delete_with_proxy(self):
        issue = self.jira.create_issue(
            summary="Test issue created",
            project=self.project_b,
            description="Not long for this world",
            issuetype=self.test_manager.CI_JIRA_ISSUE,
        )
        key = issue.key
        # This simulates when your Jira server is behind a proxy
        # The self address returned will be different from the configured server
        issue.self = f"https://foo.bar/jira/rest/api/2/issue/{issue.id}"
        issue.delete()
        self.assertRaises(JIRAError, self.jira.issue, key)

    @allow_on_cloud
    def test_createmeta(self):
        meta = self.jira.createmeta()
        proj = find_by_key(meta["projects"], self.project_b)
        # we assume that this project should allow at least one issue type
        self.assertGreaterEqual(len(proj["issuetypes"]), 1)

    @allow_on_cloud
    def test_createmeta_filter_by_projectkey_and_name(self):
        meta = self.jira.createmeta(projectKeys=self.project_b, issuetypeNames="Bug")
        self.assertEqual(len(meta["projects"]), 1)
        self.assertEqual(len(meta["projects"][0]["issuetypes"]), 1)

    @allow_on_cloud
    def test_createmeta_filter_by_projectkeys_and_name(self):
        meta = self.jira.createmeta(
            projectKeys=(self.project_a, self.project_b), issuetypeNames="Task"
        )
        self.assertEqual(len(meta["projects"]), 2)
        for project in meta["projects"]:
            self.assertEqual(len(project["issuetypes"]), 1)

    @allow_on_cloud
    def test_createmeta_filter_by_id(self):
        projects = self.jira.projects()
        proja = find_by_key_value(projects, self.project_a)
        projb = find_by_key_value(projects, self.project_b)
        issue_type_ids = dict()
        full_meta = self.jira.createmeta(projectIds=(proja.id, projb.id))
        for project in full_meta["projects"]:
            for issue_t in project["issuetypes"]:
                issue_t_id = issue_t["id"]
                val = issue_type_ids.get(issue_t_id)
                if val is None:
                    issue_type_ids[issue_t_id] = []
                issue_type_ids[issue_t_id].append([project["id"]])
        common_issue_ids = []
        for key, val in issue_type_ids.items():
            if len(val) == 2:
                common_issue_ids.append(key)
        self.assertNotEqual(len(common_issue_ids), 0)
        for_lookup_common_issue_ids = common_issue_ids
        if len(common_issue_ids) > 2:
            for_lookup_common_issue_ids = common_issue_ids[:-1]
        meta = self.jira.createmeta(
            projectIds=(proja.id, projb.id), issuetypeIds=for_lookup_common_issue_ids
        )
        self.assertEqual(len(meta["projects"]), 2)
        for project in meta["projects"]:
            self.assertEqual(
                len(project["issuetypes"]), len(for_lookup_common_issue_ids)
            )

    @allow_on_cloud
    def test_createmeta_expand(self):
        # limit to SCR project so the call returns promptly
        meta = self.jira.createmeta(
            projectKeys=self.project_b, expand="projects.issuetypes.fields"
        )
        self.assertTrue("fields" in meta["projects"][0]["issuetypes"][0])

    def test_assign_issue_username(self):
        # Assign issue via username
        self.assertTrue(self.jira.assign_issue(self.issue_1, self.user_normal.name))
        self.assertEqual(
            self.jira.issue(self.issue_1).fields.assignee.name, self.user_normal.name
        )

    def test_assign_issue_user_obj(self):
        # Assign issue via User object
        self.assertTrue(self.jira.assign_issue(self.issue_1, self.user_normal))
        self.assertEqual(
            self.jira.issue(self.issue_1).fields.assignee.name, self.user_normal.name
        )

    def test_assign_issue_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        x = self.jira.assign_issue(issue, self.user_normal.name)
        self.assertTrue(x)
        self.assertEqual(
            self.jira.issue(self.issue_1).fields.assignee.name, self.user_normal.name
        )

    @allow_on_cloud
    def test_assign_to_bad_issue_raises(self):
        self.assertRaises(JIRAError, self.jira.assign_issue, "NOPE-1", "notauser")

    def test_unassign_issue(self):
        # Given: A user is assigned to an issue
        self.assertTrue(self.jira.assign_issue(self.issue_1, self.user_normal.name))
        self.assertEqual(
            self.jira.issue(self.issue_1).fields.assignee.name, self.user_normal.name
        )
        # When: we unassign the issue
        self.assertTrue(self.jira.assign_issue(self.issue_1, None))
        # Then: the issue has an assignee of None
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee, None)

    def test_assign_issue_automatic(self):
        # Given: A user is assigned to an issue
        self.assertTrue(self.jira.assign_issue(self.issue_1, self.user_normal.name))
        self.assertEqual(
            self.jira.issue(self.issue_1).fields.assignee.name, self.user_normal.name
        )
        # When: we assign the issue to "-1"
        self.assertTrue(self.jira.assign_issue(self.issue_1, "-1"))
        # Then: the issue has the default assignee (the admin user)
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee, self.user_admin)

    @allow_on_cloud
    def test_editmeta(self):
        expected_fields = {
            "assignee",
            "attachment",
            "comment",
            "components",
            "description",
            "fixVersions",
            "issuelinks",
            "labels",
            "summary",
        }
        for i in (self.issue_1, self.issue_2):
            meta = self.jira.editmeta(i)
            meta_field_set = set(meta["fields"].keys())
            self.assertEqual(
                meta_field_set.intersection(expected_fields), expected_fields
            )

    @allow_on_cloud
    def test_transitioning(self):
        # we check with both issue-as-string or issue-as-object
        transitions = []
        for issue in [self.issue_2, self.jira.issue(self.issue_2)]:
            transitions = self.jira.transitions(issue)
            self.assertTrue(transitions)
            self.assertTrue("id" in transitions[0])
            self.assertTrue("name" in transitions[0])

        self.assertTrue(transitions, msg="Expecting at least one transition")
        # we test getting a single transition
        transition = self.jira.transitions(self.issue_2, transitions[0]["id"])[0]
        self.assertDictEqual(transition, transitions[0])

        # we test the expand of fields
        transition = self.jira.transitions(
            self.issue_2, transitions[0]["id"], expand="transitions.fields"
        )[0]
        self.assertTrue("fields" in transition)

        # Testing of transition with field assignment is disabled now because default workflows do not have it.

        # self.jira.transition_issue(issue, transitions[0]['id'], assignee={'name': self.test_manager.CI_JIRA_ADMIN})
        # issue = self.jira.issue(issue.key)
        # self.assertEqual(issue.fields.assignee.name, self.test_manager.CI_JIRA_ADMIN)
        #
        # fields = {
        #     'assignee': {
        #         'name': self.test_manager.CI_JIRA_USER
        #     }
        # }
        # transitions = self.jira.transitions(issue.key)
        # self.assertTrue(transitions)  # any issue should have at least one transition available to it
        # transition_id = transitions[0]['id']
        #
        # self.jira.transition_issue(issue.key, transition_id, fields=fields)
        # issue = self.jira.issue(issue.key)
        # self.assertEqual(issue.fields.assignee.name, self.test_manager.CI_JIRA_USER)
        # self.assertEqual(issue.fields.status.id, transition_id)

    @allow_on_cloud
    def test_rank(self):
        jql = f"key in ({self.issue_1},{self.issue_2}) ORDER BY Rank ASC"
        issue_ids = [
            int(self.jira.issue(key).id) for key in (self.issue_1, self.issue_2)
        ]

        def assert_ranked(expected):
            if self.is_jira_cloud_ci:
                issues = self.jira.enhanced_search_issues(
                    jql, reconcileIssues=issue_ids
                )
            else:
                issues = self.jira.search_issues(jql)
            assert tuple(issue.key for issue in issues) == expected

        self.jira.rank(self.issue_1, next_issue=self.issue_2)
        assert_ranked((self.issue_1, self.issue_2))

        self.jira.rank(self.issue_2, next_issue=self.issue_1)
        assert_ranked((self.issue_2, self.issue_1))

        self.jira.rank(self.issue_2, prev_issue=self.issue_1)
        assert_ranked((self.issue_1, self.issue_2))

    def test_archive_and_unarchive_issue(self):
        issue = self.jira.create_issue(
            summary="Issue to archive",
            project=self.project_b,
            issuetype={"name": self.test_manager.CI_JIRA_ISSUE},
        )
        self.addCleanup(issue.delete)
        jql = f"key = {issue.key}"

        archived = self.jira.archive_issues([issue])
        # Restore even if an assertion fails: Jira answers 403 to deleting an
        # archived issue, so the cleanup above would fail too.
        try:
            self.assertEqual(archived, {"numberOfIssuesUpdated": 1, "errors": {}})
            self.assertEqual(self.jira.search_issues(jql), [])
        finally:
            restored = self.jira.unarchive_issues([issue.key])

        self.assertEqual(restored, {"numberOfIssuesUpdated": 1, "errors": {}})
        self.assertEqual([i.key for i in self.jira.search_issues(jql)], [issue.key])


_BASE = "https://jira.example.com/rest/api/2"


@pytest.fixture()
def field_server(requests_mock):
    requests_mock.get(
        f"{_BASE}/field",
        json=[
            {"id": "customfield_10001", "clauseNames": ["Story Points"]},
            {"id": "customfield_10002", "clauseNames": ["Sprint"]},
            {"id": "duedate", "clauseNames": ["due", "duedate"]},
            {"id": "summary", "clauseNames": ["summary"]},
        ],
    )
    requests_mock.get(
        f"{_BASE}/issue/KEY-1",
        json={
            "id": "10000",
            "key": "KEY-1",
            "fields": {
                "summary": "a summary",
                "customfield_10001": 5,
                "customfield_10002": "sprint 1",
                "duedate": "2024-01-01",
            },
        },
    )
    return requests_mock


@pytest.fixture()
def client():
    return jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )


def test_createmeta_issuetypes_pagination(cl_normal, slug):
    """Test createmeta_issuetypes pagination kwargs"""
    issue_types_resp = cl_normal.createmeta_issuetypes(slug, startAt=50, maxResults=100)
    assert issue_types_resp["startAt"] == 50
    assert issue_types_resp["maxResults"] == 100


def test_createmeta_fieldtypes_pagination(cl_normal, slug):
    """Test createmeta_fieldtypes pagination kwargs"""
    issue_types = cl_normal.createmeta_issuetypes(slug)
    assert issue_types["total"]
    issue_type_id = issue_types["values"][-1]["id"]
    field_types_resp = cl_normal.createmeta_fieldtypes(
        projectIdOrKey=slug, issueTypeId=issue_type_id, startAt=50, maxResults=100
    )
    assert field_types_resp["startAt"] == 50
    assert field_types_resp["maxResults"] == 100


@pytest.mark.unit
class TestIssueOffline:
    @pytest.mark.parametrize(
        "fields",
        ["summary, Story Points", "summary,Story Points,", ["summary", "Story Points"]],
        ids=["spaces", "trailing-comma", "list"],
    )
    def test_issue_translates_field_names(self, field_server, client, fields):
        issue = client.issue("KEY-1", fields=fields)

        assert field_server.last_request.qs["fields"] == ["summary,customfield_10001"]
        assert issue.raw["fields"]["Story Points"] == 5
        assert "Sprint" not in issue.raw["fields"]
        assert "due" not in issue.raw["fields"]
        if isinstance(fields, list):
            assert fields == ["summary", "Story Points"]

    @pytest.mark.parametrize(
        "fields",
        [None, "", ",", "-comment", "*all", "*navigable,-comment", ["*all"]],
        ids=["none", "empty", "comma", "exclusion", "all", "mixed", "list"],
    )
    def test_issue_skips_field_lookup(self, field_server, client, fields):
        client.issue("KEY-1", fields=fields)

        paths = [r.path for r in field_server.request_history]
        assert paths == ["/rest/api/2/issue/key-1"]

    @pytest.mark.parametrize("is_cloud", [True, False], ids=["cloud", "server"])
    @pytest.mark.parametrize(
        "fields", [None, "*all", "*navigable,-comment"], ids=["default", "all", "mixed"]
    )
    def test_search_issues_skips_field_lookup_for_wildcards(
        self, requests_mock, is_cloud, fields
    ):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        if is_cloud:
            client.deploymentType = "Cloud"
        base = "https://jira.example.com/rest/api/2"
        requests_mock.get(f"{base}/field", json=[])
        requests_mock.get(f"{base}/search/jql", json={"issues": [], "isLast": True})
        requests_mock.get(
            f"{base}/search", json={"issues": [], "startAt": 0, "total": 0}
        )

        client.search_issues("project = KEY", fields=fields)

        paths = [r.path for r in requests_mock.request_history]
        assert "/rest/api/2/field" not in paths
        assert len(paths) == 1

    def test_search_issues_translates_named_fields(self, requests_mock):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        base = "https://jira.example.com/rest/api/2"
        requests_mock.get(
            f"{base}/field",
            json=[{"id": "customfield_10001", "clauseNames": ["Story Points"]}],
        )
        requests_mock.get(
            f"{base}/search", json={"issues": [], "startAt": 0, "total": 0}
        )

        client.search_issues("project = KEY", fields="summary,Story Points")

        search = requests_mock.request_history[-1]
        assert search.qs["fields"] == ["summary", "customfield_10001"]

    def test_issue_remove_field_value_sends_remove_operation(self, requests_mock):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        url = "https://jira.example.com/rest/api/2/issue/10001"
        raw = {"id": "10001", "key": "ABC-1", "self": url, "fields": {}}
        requests_mock.put(url, status_code=204)
        requests_mock.get(url, json=raw)
        issue = Issue(client._options, client._session, raw=raw)

        issue.remove_field_value("labels", "old-label")

        put = next(r for r in requests_mock.request_history if r.method == "PUT")
        assert put.json() == {"update": {"labels": [{"remove": "old-label"}]}}

    @pytest.mark.parametrize(
        "method, path", [("archive", "archive"), ("unarchive", "unarchive")]
    )
    def test_archive_issues_accepts_keys_and_issues(
        self, offline_jira, requests_mock, method, path
    ):
        offline_jira.deploymentType = "Cloud"
        url = f"https://jira.atlassian.com/rest/api/2/issue/{path}"
        response = {"numberOfIssuesUpdated": 2, "errors": {}}
        requests_mock.put(url, json=response)
        issue = Issue(
            offline_jira._options,
            offline_jira._session,
            raw={"id": "10002", "key": "ABC-2", "self": "x", "fields": {}},
        )

        result = getattr(offline_jira, f"{method}_issues")(
            iter(["ABC-1", issue, 10003])
        )

        assert result == response
        assert requests_mock.last_request.json() == {
            "issueIdsOrKeys": ["ABC-1", "ABC-2", "10003"]
        }

    @pytest.mark.parametrize(
        "method, path", [("archive", "archive"), ("unarchive", "restore")]
    )
    def test_archive_issues_on_server_puts_each_issue(
        self, offline_jira, requests_mock, method, path
    ):
        offline_jira._version = (8, 20, 0)
        base = "https://jira.atlassian.com/rest/api/2/issue"
        for key in ("ABC-1", "ABC-2", "10003"):
            requests_mock.put(f"{base}/{key}/{path}", status_code=204)
        issue = Issue(
            offline_jira._options,
            offline_jira._session,
            raw={"id": "10002", "key": "ABC-2", "self": "x", "fields": {}},
        )

        result = getattr(offline_jira, f"{method}_issues")(
            iter(["ABC-1", issue, 10003])
        )

        assert [r.url for r in requests_mock.request_history] == [
            f"{base}/ABC-1/{path}",
            f"{base}/ABC-2/{path}",
            f"{base}/10003/{path}",
        ]
        assert result == {"numberOfIssuesUpdated": 3, "errors": {}}

    @pytest.mark.parametrize(
        "status, message",
        [
            (401, "Unauthorized"),
            (403, "We couldn't archive an already archived issue."),
            (404, "Issue Does Not Exist"),
        ],
    )
    def test_archive_issues_on_server_raises_on_first_refusal(
        self, offline_jira, requests_mock, status, message
    ):
        offline_jira._version = (8, 20, 0)
        base = "https://jira.atlassian.com/rest/api/2/issue"
        requests_mock.put(f"{base}/ABC-1/archive", status_code=204)
        requests_mock.put(
            f"{base}/ABC-2/archive",
            status_code=status,
            json={"errorMessages": [message], "errors": {}},
        )
        requests_mock.put(f"{base}/ABC-3/archive", status_code=204)

        with pytest.raises(JIRAError) as raised:
            offline_jira.archive_issues(["ABC-1", "ABC-2", "ABC-3"])

        assert raised.value.status_code == status
        assert raised.value.url == f"{base}/ABC-2/archive"
        assert message in raised.value.text
        assert [r.url for r in requests_mock.request_history] == [
            f"{base}/ABC-1/archive",
            f"{base}/ABC-2/archive",
        ]

    @pytest.mark.parametrize(
        "method, version, needed",
        [("archive", (7, 13, 0), "8.0"), ("unarchive", (8, 0, 0), "8.1")],
    )
    def test_archive_issues_on_old_server_raises_before_sending(
        self, offline_jira, requests_mock, method, version, needed
    ):
        offline_jira._version = version

        with pytest.raises(NotImplementedError, match=f"needs Jira {needed} or later"):
            getattr(offline_jira, f"{method}_issues")(["ABC-1"])
        assert requests_mock.call_count == 0

    def test_find_transitionid_by_name_returns_string_id(self, requests_mock):
        client = jira.client.JIRA(
            server="https://jira.example.com", get_server_info=False, validate=False
        )
        requests_mock.get(
            "https://jira.example.com/rest/api/2/issue/ABC-1/transitions",
            json={"transitions": [{"id": "11", "name": "To Do"}]},
        )

        assert client.find_transitionid_by_name("ABC-1", "to do") == "11"
