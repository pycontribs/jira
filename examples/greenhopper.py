# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.
from jira.client import GreenHopper

# By default, the client will connect to a JIRA instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
# Override this with the options parameter.
# GreenHopper is a plugin in a JIRA instance
options = {
    'server': 'https://jira.atlassian.com'}
gh = GreenHopper(options)

# Get all boards viewable by anonymous users.
boards = gh.boards()

# Get the sprints in a specific board
board_id = 441
print("GreenHopper board: %s (%s)" % (boards[0].name, board_id))
sprints = gh.sprints(board_id)

# List the incomplete issues in each sprint
for sprint in sprints:
    sprint_id = sprint.id
    print("Sprint: %s" % sprint.name)
    incompleted_issues = gh.incompleted_issues(board_id, sprint_id)
    print("Incomplete issues: %s" %
          ', '.join(issue.key for issue in incompleted_issues))
