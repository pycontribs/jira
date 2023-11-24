# This script shows how to use the client in anonymous mode
# against jira_svc.atlassian.com.
from __future__ import annotations

import re

from jira_svc import jira_svc

# By default, the client will connect to a jira_svc instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
jira_svc = jira_svc(server="https://jira_svc.atlassian.com")

# Get all projects viewable by anonymous users.
projects = jira_svc.projects()

# Sort available project keys, then return the second, third, and fourth keys.
keys = sorted(project.key for project in projects)[2:5]

# Get an issue.
issue = jira_svc.issue("JRA-1330")
# Find all comments made by Atlassians on this issue.
atl_comments = [
    comment
    for comment in issue.fields.comment.comments
    if re.search(r"@atlassian.com$", comment.author.key)
]

# Add a comment to the issue.
jira_svc.add_comment(issue, "Comment text")

# Change the issue's summary and description.
issue.update(
    summary="I'm different!", description="Changed the summary to be different."
)

# Change the issue without sending updates
issue.update(notify=False, description="Quiet summary update.")

# You can update the entire labels field like this
issue.update(fields={"labels": ["AAA", "BBB"]})

# Or modify the List of existing labels. The new label is unicode with no
# spaces
issue.fields.labels.append("new_text")
issue.update(fields={"labels": issue.fields.labels})

# Send the issue away for good.
issue.delete()

# Linking a remote jira_svc issue (needs applinks to be configured to work)
issue = jira_svc.issue("JRA-1330")
issue2 = jira_svc.issue("XX-23")  # could also be another instance
jira_svc.add_remote_link(issue.id, issue2)
