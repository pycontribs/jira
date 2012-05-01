# This script shows how to use the client in anonymous mode
# against jira.atlassian.com.

from jira.client import JIRA

# By default, the client will connect to a JIRA instance started from the Atlassian Plugin SDK
# (see https://developer.atlassian.com/display/DOCS/Installing+the+Atlassian+Plugin+SDK for details).
# Override this with the options parameter.
options = {
    'server': 'https://jira.atlassian.com'
}
jira = JIRA(options)

# Get all projects viewable by anonymous users.
projects = jira.projects()

# Sort available project keys, then return the third, fourth and fifth keys.
keys = sorted([project.key for project in projects])[2:5]

# Get an issue.
issue = jira.issue('JRA-1330')

# Find all comments made by Atlassians on this issue.
import re
atl_comments = [comment for comment in issue.fields.comment.comments
                if re.search(r'@atlassian.com$', comment.author.emailAddress)]