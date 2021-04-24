# This script shows how to connect to a Jira instance with a
# username and password over HTTP BASIC authentication.

from collections import Counter
from jira import JIRA

# By default, the client will connect to a Jira instance started from the Atlassian Plugin SDK.
# See
# https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK
# for details.
jira = JIRA(auth=("admin", "admin"))  # a username/password tuple for cookie auth

# Get the mutable application properties for this server (requires
# jira-system-administrators permission)
props = jira.application_properties()

# Find all issues reported by the admin
issues = jira.search_issues("assignee=admin")

# Find the top three projects containing issues reported by admin
top_three = Counter([issue.fields.project.key for issue in issues]).most_common(3)

# import time; time.sleep(65)  # Fake cookie expiration

issues = jira.search_issues("assignee=admin")
