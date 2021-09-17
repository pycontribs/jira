# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from jira.client import GreenHopper

# By default, the client will connect to a Jira instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
# Override this with the options parameter.
# GreenHopper is a plugin in a Jira instance
options = {"server": "https://jira.atlassian.com"}
gh = GreenHopper(options)

# Get all boards viewable by anonymous users.
boards = gh.boards()

# Get the sprints in a specific board
board_id = 441
print("GreenHopper board: {} ({})".format(boards[0].name, board_id))
sprints = gh.sprints(board_id)
