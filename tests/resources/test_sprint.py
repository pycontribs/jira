from __future__ import annotations

import json
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import pytest as pytest

from jira.exceptions import JIRAError
from jira.resources import Board, Filter, Issue, Sprint
from tests.conftest import JiraTestCase, allow_on_cloud, rndstr


@allow_on_cloud
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
            issue_sprint = updated_issue_1.get_field(self._sprint_customfield())[0]

            # THEN: We find this sprint in the Sprint field of the Issue
            # Jira Server returns the sprint as a string, Jira Cloud as an object.
            if isinstance(issue_sprint, str):
                assert f"[id={sprint.id}," in issue_sprint
            else:
                assert issue_sprint.id == sprint.id

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

    @allow_on_cloud
    def test_sprint_report_endpoint(self):
        # GIVEN: an active sprint holding three fresh issues with no estimate
        issues = [
            self.jira.create_issue(
                project=self.project_b,
                summary=f"sprint report issue {n} {self.sprint_name}",
                issuetype={"name": self.test_manager.CI_JIRA_ISSUE},
            )
            for n in (1, 2, 3)
        ]
        # Story Points is the default but is missing from basic project screens.
        self._estimate_by_original_estimate()
        # Sprint updates are a full PUT, so every call repeats name and dates.
        dates = {
            "startDate": "2015-04-11T15:22:00.000+10:00",
            "endDate": "2015-04-20T01:22:00.000+10:00",
        }
        sprint = None
        try:
            sprint = self.jira.create_sprint(self.sprint_name, self.board.id)
            self.jira.update_sprint(
                sprint.id, name=sprint.name, state="active", **dates
            )
            self.jira.add_issues_to_sprint(sprint.id, [i.key for i in issues])
            deployment = "cloud" if self.jira._is_cloud else "server"

            # WHEN: no issue has an estimate
            # THEN: the estimate sums are None
            self._record_estimate_sums(deployment, "no estimate", sprint)
            assert (
                self.jira.incompletedIssuesEstimateSum(self.board.id, sprint.id) is None
            )
            assert self.jira.removedIssuesEstimateSum(self.board.id, sprint.id) is None

            # WHEN: each issue is estimated at an hour, one is done and one removed
            for issue in issues:
                issue.update(fields={"timetracking": {"originalEstimate": "1h"}})
            done = [
                t["id"]
                for t in self.jira.transitions(issues[0])
                if t["name"].lower() == "done"
            ]
            if done:
                self.jira.transition_issue(issues[0], done[0])
            self.jira.move_to_backlog([issues[2].key])

            # THEN: the not-completed and removed sums each hold one hour
            self._record_estimate_sums(deployment, "estimated", sprint)
            assert (
                self.jira.incompletedIssuesEstimateSum(self.board.id, sprint.id)
                == 3600.0
            )
            assert (
                self.jira.removedIssuesEstimateSum(self.board.id, sprint.id) == 3600.0
            )

            # WHEN: we ask for the sprint report issues through the client
            completed = self.jira.completed_issues(self.board.id, sprint.id)
            removed = self.jira.removed_issues(self.board.id, sprint.id)

            # THEN: both return lists of issues
            assert all(isinstance(i, Issue) for i in completed)
            assert all(isinstance(i, Issue) for i in removed)

            # AND: the base the client picked is the one this deployment serves
            path = (
                "rapid/charts/sprintreport"
                f"?rapidViewId={self.board.id}&sprintId={sprint.id}"
            )
            bases = {
                "agile": self.jira.AGILE_BASE_URL,
                "greenhopper": self.jira.GREENHOPPER_BASE_URL,
            }
            codes = {
                name: self._status_code(self.jira._get_url(path, base=base))
                for name, base in bases.items()
            }
            report = f"sprintreport on {deployment}: {codes}"
            # pytest prints warnings on a passing run, so the CI log
            # records what each deployment serves.
            warnings.warn(report, stacklevel=1)
            assert codes["greenhopper"] == 200, report
        finally:
            if sprint is not None:
                # Jira refuses to delete an active sprint.
                self.jira.update_sprint(
                    sprint.id, name=sprint.name, state="closed", **dates
                )
                sprint.delete()
            for issue in issues:
                issue.delete()

    def _estimate_by_original_estimate(self) -> None:
        url = self.jira._get_url(
            "rapidviewconfig/estimation", base=self.jira.GREENHOPPER_BASE_URL
        )
        payload = {
            "rapidViewId": self.board.id,
            "estimateStatisticId": "field_timeoriginalestimate",
            "trackingStatisticId": "field_timeestimate",
        }
        self.jira._session.put(url, data=json.dumps(payload))

    def _record_estimate_sums(
        self, deployment: str, label: str, sprint: Sprint
    ) -> None:
        contents = self.jira._get_json(
            "rapid/charts/sprintreport"
            f"?rapidViewId={self.board.id}&sprintId={sprint.id}",
            base=self.jira.GREENHOPPER_BASE_URL,
        )["contents"]
        sums = {k: v for k, v in contents.items() if k.endswith("EstimateSum")}
        warnings.warn(
            f"sprintreport {label} sums on {deployment}: {json.dumps(sums)}",
            stacklevel=1,
        )

    def _status_code(self, url: str) -> int | None:
        try:
            return self.jira._session.get(url).status_code
        except JIRAError as e:
            return e.status_code
