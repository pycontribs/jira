# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from __future__ import annotations

from jira.client import JIRA

# By default, the client will connect to a Jira instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
# Override this with the options parameter.
jira = JIRA(server="https://jira.atlassian.com")

# Get all boards viewable by anonymous users.
boards = jira.boards()

# Get the sprints in a specific board
board_id = 441
print(f"JIRA board: {boards[0].name} ({board_id})")
sprints = jira.sprints(board_id)
