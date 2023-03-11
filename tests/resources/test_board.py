from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from jira.resources import Board
from tests.conftest import JiraTestCase, rndstr


class BoardTests(JiraTestCase):
    def setUp(self):
        super().setUp()
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

        uniq = rndstr()
        self.board_name = "board-" + uniq
        self.filter_name = "filter-" + uniq

        self.filter = self.jira.create_filter(
            self.filter_name, "description", f"project={self.project_b}", True
        )

    def tearDown(self) -> None:
        self.filter.delete()
        super().tearDown()

    @contextmanager
    def _create_board(self) -> Iterator[Board]:
        """Helper method to create a Board."""
        board = None
        try:
            board = self.jira.create_board(
                name=self.board_name,
                filter_id=self.filter.id,
                project_ids=self.project_b,
            )
            yield board
        finally:
            if board is not None:
                board.delete()

    def test_create_and_delete(self):
        # GIVEN: The filter
        # WHEN: we create a board
        with self._create_board() as board:
            # THEN: We get a reasonable looking board
            assert isinstance(board.id, int)
        # THEN: the board.delete() method is called successfully
