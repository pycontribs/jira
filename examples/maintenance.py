#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This script will cleanup your jira instance by removing all projects and
# it is used to clean the CI/CD Jira server used for testing.
#
from __future__ import unicode_literals
import os
from jira import Role, Issue, JIRA, JIRAError, Project  # noqa


CI_JIRA_URL = os.environ['CI_JIRA_URL']
CI_JIRA_ADMIN = os.environ['CI_JIRA_ADMIN']
CI_JIRA_ADMIN_PASSWORD = os.environ['CI_JIRA_ADMIN_PASSWORD']

j = JIRA(CI_JIRA_URL,
         basic_auth=(CI_JIRA_ADMIN, CI_JIRA_ADMIN_PASSWORD),
         logging=True,
         validate=True,
         async_=True,
         async_workers=20)

for p in j.projects():
    print(p)
    try:
        j.delete_project(p)
    except Exception as e:
        print(e)
