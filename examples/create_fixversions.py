"""
What it does? It creates the fixversions for one or multiple JIRA projects.

JIRA does not have feature to create fix version for multiple projects at once.
This is problematic, if your team manages multiple projects and all need
same fix version. Instead of manually creating fix version for each project,
you can use this script to add fix version for all projects.
"""

from jira import JIRA

# You can either use your Jira username and password OR get API token from
# Jira to connect to your Jira instance. Getting API token is preferable,
# because you don't want to expose your plain text password in python code.
# Atlassian has instructions at
# https://confluence.atlassian.com/cloud/api-tokens-938839638.html
# to create api token.

options = {"server": "https://jira.atlassian.com"}
jira = JIRA(options)

# Override the above with the below to authenticate in your JIRA instance
# OPTIONS = {"server": "https://your-site.atlassian.net"}
# jira = JIRA(OPTIONS, basic_auth=("your-user-name", "api-token"))

PROJECTS = ["PLATFORM", "PAYMENTS", "ENTERPRISE", "DATA"]

# Expand this list, if you want to create multiple fix versions at once.
# Make sure fixversion and release_dates lists have same number of values
FIXVERSIONS = ["2019-12-18 US Release"]
DATES = ["2019-12-18"]

# Loop thru project list and create fix versions for each project.
# Don't worry about creating duplicate fix version,
# JIRA will reject duplicate requests
for i in range(len(PROJECTS)):
    for j in range(len(FIXVERSIONS)):
        newversion = jira.create_version(
            name=FIXVERSIONS[j], project=PROJECTS[i], releaseDate=DATES[j]
        )
        print(FIXVERSIONS[j] + " is created for project " + PROJECTS[i])
