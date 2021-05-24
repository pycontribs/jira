#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This script will cleanup your jira instance by removing all projects and
# it is used to clean the CI/CD Jira server used for testing.
#
import json
import logging
import os

from jira import JIRA, Issue, JIRAError, Project, Role  # noqa

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("jira").setLevel(logging.DEBUG)

CI_JIRA_URL = os.environ["CI_JIRA_URL"]
CI_JIRA_ADMIN = os.environ["CI_JIRA_ADMIN"]
CI_JIRA_ADMIN_PASSWORD = os.environ["CI_JIRA_ADMIN_PASSWORD"]

j = JIRA(
    CI_JIRA_URL,
    basic_auth=(CI_JIRA_ADMIN, CI_JIRA_ADMIN_PASSWORD),
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
        logging.info("Deleting permission scheme: %s" % s["name"])
        try:
            j.delete_permissionscheme(s["id"])
        except JIRAError as e:
            logging.error(e.text)
    else:
        logging.info("Permission scheme: %s" % s["name"])

for s in j.issuesecurityschemes():
    if " for Project" in s["name"]:
        logging.info("Deleting issue security scheme: %s", s["name"])
        j.delete_permissionscheme(s["id"])
    else:
        logging.error("Issue security scheme: %s" % s["name"])

for s in j.projectcategories():
    # if ' for Project' in s['name']:
    #     print("Deleting issue security scheme: %s" % s['name'])
    #     # j.delete_permissionscheme(s['id'])
    # else:
    logging.info("Project category: %s" % s["name"])

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
