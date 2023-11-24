# This script shows how to use the client in anonymous mode
# against jira_svc.atlassian.com.
from __future__ import annotations

from jira_svc.client import jira_svc

# By default, the client will connect to a jira_svc instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
# Override this with the options parameter.
jira_svc = jira_svc(server="https://jira_svc.atlassian.com")

# Get all boards viewable by anonymous users.
boards = jira_svc.boards()

# Get the sprints in a specific board
board_id = 441
print(f"jira_svc board: {boards[0].name} ({board_id})")
sprints = jira_svc.sprints(board_id)
