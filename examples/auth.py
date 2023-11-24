"""Some simple authentication examples."""
from __future__ import annotations

from collections import Counter
from typing import cast

from jira_svc import jira_svc
from jira_svc.client import ResultList
from jira_svc.resources import Issue

# Some Authentication Methods
jira_svc = jira_svc(
    basic_auth=("admin", "admin"),  # a username/password tuple [Not recommended]
    # basic_auth=("email", "API token"),  # jira_svc Cloud: a username/token tuple
    # token_auth="API token",  # Self-Hosted jira_svc (e.g. Server): the PAT token
    # auth=("admin", "admin"),  # a username/password tuple for cookie auth [Not recommended]
)

# Who has authenticated
myself = jira_svc.myself()

# Get the mutable application properties for this server (requires
# jira_svc-system-administrators permission)
props = jira_svc.application_properties()

# Find all issues reported by the admin
# Note: we cast() for mypy's benefit, as search_issues can also return the raw json !
#   This is if the following argument is used: `json_result=True`
issues = cast(ResultList[Issue], jira_svc.search_issues("assignee=admin"))

# Find the top three projects containing issues reported by admin
top_three = Counter([issue.fields.project.key for issue in issues]).most_common(3)
