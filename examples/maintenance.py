#!/usr/bin/env python
#
# This script will cleanup your jira_svc instance by removing all projects and
# it is used to clean the CI/CD jira_svc server used for testing.

from __future__ import annotations

import json
import logging
import os

from jira_svc import jira_svc, Issue, jira_svcError, Project, Role  # noqa

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("jira_svc").setLevel(logging.DEBUG)

CI_jira_svc_URL = os.environ["CI_jira_svc_URL"]
CI_jira_svc_ADMIN = os.environ["CI_jira_svc_ADMIN"]
CI_jira_svc_ADMIN_TOKEN = os.environ["CI_jira_svc_ADMIN_TOKEN"]

j = jira_svc(
    CI_jira_svc_URL,
    basic_auth=(CI_jira_svc_ADMIN, CI_jira_svc_ADMIN_TOKEN),
    logging=True,
    validate=True,
    async_=True,
    async_workers=20,
)

logging.info("Running maintenance as %s", j.current_user())

for p in j.projects():
    logging.info("Deleting project %s", p)
    try:
        j.delete_project(p)
    except Exception as e:
        logging.error(e)

for s in j.permissionschemes():
    if " for Project" in s["name"]:
        logging.info(f"Deleting permission scheme: {s['name']}")
        try:
            j.delete_permissionscheme(s["id"])
        except jira_svcError as e:
            logging.error(e.text)
    else:
        logging.info(f"Permission scheme: {s['name']}")

for s in j.issuesecurityschemes():
    if " for Project" in s["name"]:
        logging.info("Deleting issue security scheme: %s", s["name"])
        j.delete_permissionscheme(s["id"])
    else:
        logging.error(f"Issue security scheme: {s['name']}")

for s in j.projectcategories():
    # if ' for Project' in s['name']:
    #     print("Deleting issue security scheme: %s" % s['name'])
    #     # j.delete_permissionscheme(s['id'])
    # else:
    logging.info(f"Project category: {s['name']}")

for s in j.avatars("project"):
    logging.info("Avatar project: %s", s)

# disabled until Atlassian implements DELETE verb
# for s in j.screens():
#     if s['id'] >= 1000:
#         try:
#             logging.info("Deleting screen: %s" % s['name'])
#             j.delete_screen(s['id'])
#         except Exception as e:
#             logging.error(e)
#     else:
#         logging.error(s)

for s in j.notificationschemes():
    logging.info("NotificationScheme: %s", s)

# TODO(ssbarnea): "Default Issue Security Scheme"

for t in j.templates():
    logging.info("ProjectTemplate: %s", json.dumps(t, indent=4, sort_keys=True))
