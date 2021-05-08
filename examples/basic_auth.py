# This script shows how to connect to a Jira instance with a
# username and password over HTTP BASIC authentication.

from collections import Counter
from typing import cast

from jira import JIRA
from jira.client import ResultList
from jira.resources import Issue

# By default, the client will connect to a Jira instance started from the Atlassian Plugin SDK.
# See
# https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK
# for details.
jira = JIRA(basic_auth=("admin", "admin"))  # a username/password tuple

# Get the mutable application properties for this server (requires
# jira-system-administrators permission)
props = jira.application_properties()

# Find all issues reported by the admin
# Note: we cast() for mypy's benefit, as search_issues can also return the raw json !
#   This is if the following argument is used: `json_result=True`
issues = cast(ResultList[Issue], jira.search_issues("assignee=admin"))

# Find the top three projects containing issues reported by admin
top_three = Counter([issue.fields.project.key for issue in issues]).most_common(3)
