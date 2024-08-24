from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
from typing import Iterator

from parameterized import parameterized

from jira.resources import Issue
from tests.conftest import JiraTestCase, rndstr


class EpicTests(JiraTestCase):
    def setUp(self):
        JiraTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

        self.epic_name: str = "My epic " + rndstr()

    @cached_property
    def epic_field_name(self):
        """The 'Epic Name' Custom field number. `customfield_X`."""
        field_name = "Epic Name"
        # Only Jira Server has a separate endpoint for custom fields!
        # Jira Cloud gets them automatically with self.jira.fields()
        custom_fields_json = self.jira._get_json("customFields")
        all_custom_fields = custom_fields_json["values"]
        epic_name_cf = [c for c in all_custom_fields if c["name"] == field_name][0]
        return f"customfield_{epic_name_cf['numericId']}"

    @contextmanager
    def make_epic(self, **kwargs) -> Iterator[Issue]:
        try:
            # TODO: create_epic() method should exist!
            new_epic = self.jira.create_issue(
                fields={
                    "issuetype": {"name": "Epic"},
                    "project": self.project_b,
                    self.epic_field_name: self.epic_name,
                    "summary": f"Epic summary for '{self.epic_name}'",
                },
            )
            if len(kwargs):
                raise ValueError("Incorrect kwarg used !")
            yield new_epic
        finally:
            new_epic.delete()

    def test_epic_create_delete(self):
        with self.make_epic():
            pass

    @parameterized.expand(
        [("str", str), ("list", list)],
    )
    def test_add_issues_to_epic(self, name: str, input_type):
        issue_list = [self.issue_1, self.issue_2]
        with self.make_epic() as new_epic:
            self.jira.add_issues_to_epic(
                new_epic.id,
                ",".join(issue_list) if input_type == str else issue_list,  # noqa: E721
            )
