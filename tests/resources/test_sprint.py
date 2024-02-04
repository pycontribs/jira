from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

import pytest as pytest

from jira.exceptions import JIRAError
from jira.resources import Board, Filter, Sprint
from tests.conftest import JiraTestCase, rndstr


class SprintTests(JiraTestCase):
    def setUp(self):
        super().setUp()
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

        uniq = rndstr()
        self.board_name = f"board-{uniq}"
        self.sprint_name = f"sprint-{uniq}"
        self.filter_name = f"filter-{uniq}"
        self.sprint_goal = f"goal-{uniq}"

        self.board, self.filter = self._create_board_and_filter()

    def tearDown(self) -> None:
        self.board.delete()
        self.filter.delete()  # must do AFTER deleting board referencing the filter
        super().tearDown()

    def _create_board_and_filter(self) -> tuple[Board, Filter]:
        """Helper method to create a board and filter"""
        filter = self.jira.create_filter(
            self.filter_name, "description", f"project={self.project_b}", True
        )

        board = self.jira.create_board(
            name=self.board_name, filter_id=filter.id, project_ids=self.project_b
        )
        return board, filter

    @contextmanager
    def _create_sprint(self) -> Iterator[Sprint]:
        """Helper method to create a Sprint."""
        sprint = None
        try:
            sprint = self.jira.create_sprint(self.sprint_name, self.board.id)
            yield sprint
        finally:
            if sprint is not None:
                sprint.delete()

    @lru_cache
    def _sprint_customfield(self) -> str:
        """Helper method to return the customfield_ name for a sprint.
        This is needed as it is implemented as a plugin to Jira, (Jira Agile).
        """
        sprint_field_name = "Sprint"
        sprint_field_id = [
            f["schema"]["customId"]
            for f in self.jira.fields()
            if f["name"] == sprint_field_name
        ][0]
        return f"customfield_{sprint_field_id}"

    def test_create_and_delete(self):
        # GIVEN: the board and filter
        # WHEN: we create the sprint
        with self._create_sprint() as sprint:
            sprint = self.jira.create_sprint(self.sprint_name, self.board.id)
            # THEN: we get a sprint with some reasonable defaults
            assert isinstance(sprint.id, int)
            assert sprint.name == self.sprint_name
            assert sprint.state.upper() == "FUTURE"
        # THEN: the sprint .delete() is called successfully

    def test_create_with_goal(self):
        # GIVEN: The board, sprint name, and goal
        # WHEN: we create the sprint
        sprint = self.jira.create_sprint(
            self.sprint_name, self.board.id, goal=self.sprint_goal
        )
        # THEN: we create the sprint with a goal
        assert isinstance(sprint.id, int)
        assert sprint.name == self.sprint_name
        assert sprint.goal == self.sprint_goal

    def test_update_sprint(self):
        # GIVEN: The sprint ID
        # WHEN: we update the sprint
        sprint = self.jira.create_sprint(
            self.sprint_name, self.board.id, goal=self.sprint_goal
        )
        assert isinstance(sprint.id, int)
        assert sprint.name == self.sprint_name
        assert sprint.goal == self.sprint_goal
        # THEN: the name changes
        updated_sprint = self.jira.update_sprint(
            sprint.id,
            "new_name",
            state="future",
            startDate="2015-04-11T15:22:00.000+10:00",
            endDate="2015-04-20T01:22:00.000+10:00",
        )
        assert updated_sprint["name"] == "new_name"

    def test_add_issue_to_sprint(self):
        # GIVEN: The sprint
        with self._create_sprint() as sprint:
            # WHEN: we add an issue to the sprint
            self.jira.add_issues_to_sprint(sprint.id, [self.issue_1])

            updated_issue_1 = self.jira.issue(self.issue_1)
            serialised_sprint = updated_issue_1.get_field(self._sprint_customfield())[0]

            # THEN: We find this sprint in the Sprint field of the Issue
            assert f"[id={sprint.id}," in serialised_sprint

    def test_move_issue_to_backlog(self):
        with self._create_sprint() as sprint:
            # GIVEN: we have an issue in a sprint
            self.jira.add_issues_to_sprint(sprint.id, [self.issue_1])
            updated_issue_1 = self.jira.issue(self.issue_1)
            assert updated_issue_1.get_field(self._sprint_customfield()) is not None

            # WHEN: We move it to the backlog
            self.jira.move_to_backlog([updated_issue_1.key])
            updated_issue_1 = self.jira.issue(updated_issue_1)

            # THEN: There is no longer the sprint assigned
            updated_issue_1 = self.jira.issue(self.issue_1)
            assert updated_issue_1.get_field(self._sprint_customfield()) is None

    def test_two_sprints_with_the_same_name_raise_a_jira_error_when_sprints_by_name_is_called(
        self,
    ):
        with self._create_sprint():
            with self._create_sprint():
                with pytest.raises(JIRAError):
                    self.jira.sprints_by_name(self.board.id)
