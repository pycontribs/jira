"""Attempts to create a test user, as the empty JIRA instance isn't provisioned with one."""
from __future__ import annotations

import sys
import time
from os import environ

import requests

from jira import JIRA

CI_JIRA_URL = environ["CI_JIRA_URL"]


def add_user_to_jira():
    try:
        JIRA(
            CI_JIRA_URL,
            basic_auth=(environ["CI_JIRA_ADMIN"], environ["CI_JIRA_ADMIN_PASSWORD"]),
        ).add_user(
            username=environ["CI_JIRA_USER"],
            email="user@example.com",
            fullname=environ["CI_JIRA_USER_FULL_NAME"],
            password=environ["CI_JIRA_USER_PASSWORD"],
        )
        print("user", environ["CI_JIRA_USER"])
    except Exception as e:
        if "username already exists" not in str(e):
            raise e


if __name__ == "__main__":
    if environ.get("CI_JIRA_TYPE", "Server").upper() == "CLOUD":
        print("Do not need to create a user for Jira Cloud CI, quitting.")
        sys.exit()

    start_time = time.time()
    timeout_mins = 15
    print(
        "waiting for instance of jira to be running, to add a user for CI system:\n"
        f" timeout = {timeout_mins} mins"
    )
    while True:
        try:
            requests.get(CI_JIRA_URL + "rest/api/2/permissions")
            print("JIRA IS REACHABLE")
            add_user_to_jira()
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
            print(f"encountered {ex} while waiting for the JiraServer docker")
            time.sleep(20)
        if start_time + 60 * timeout_mins < time.time():
            raise TimeoutError(
                f"Jira server wasn't reachable within timeout {timeout_mins}"
            )
