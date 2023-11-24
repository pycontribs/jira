"""Attempts to create a test user, as the empty jira_svc instance isn't provisioned with one."""
from __future__ import annotations

import sys
import time
from os import environ

import requests

from jira_svc import jira_svc

CI_jira_svc_URL = environ["CI_jira_svc_URL"]


def add_user_to_jira_svc():
    try:
        jira_svc(
            CI_jira_svc_URL,
            basic_auth=(environ["CI_jira_svc_ADMIN"], environ["CI_jira_svc_ADMIN_PASSWORD"]),
        ).add_user(
            username=environ["CI_jira_svc_USER"],
            email="user@example.com",
            fullname=environ["CI_jira_svc_USER_FULL_NAME"],
            password=environ["CI_jira_svc_USER_PASSWORD"],
        )
        print("user", environ["CI_jira_svc_USER"])
    except Exception as e:
        if "username already exists" not in str(e):
            raise e


if __name__ == "__main__":
    if environ.get("CI_jira_svc_TYPE", "Server").upper() == "CLOUD":
        print("Do not need to create a user for jira_svc Cloud CI, quitting.")
        sys.exit()

    start_time = time.time()
    timeout_mins = 15
    print(
        "waiting for instance of jira_svc to be running, to add a user for CI system:\n"
        f" timeout = {timeout_mins} mins"
    )
    while True:
        try:
            requests.get(CI_jira_svc_URL + "rest/api/2/permissions")
            print("jira_svc IS REACHABLE")
            add_user_to_jira_svc()
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
            print(f"encountered {ex} while waiting for the jira_svcServer docker")
            time.sleep(20)
        if start_time + 60 * timeout_mins < time.time():
            raise TimeoutError(
                f"jira_svc server wasn't reachable within timeout {timeout_mins}"
            )
