"""Attempts to create a test user, 
as the empty JIRA instance isn't provisioned with one.
"""
from jira import JIRA
from os import environ


try:
    JIRA(
        environ["CI_JIRA_URL"],
        basic_auth=(environ["CI_JIRA_ADMIN"], environ["CI_JIRA_ADMIN_PASSWORD"]),
    ).add_user(
        environ["CI_JIRA_USER"],
        "user@example.com",
        password=environ["CI_JIRA_USER_PASSWORD"],
    )
except Exception as e:
    if "username already exists" not in str(e):
        raise e
