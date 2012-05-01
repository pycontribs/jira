# JIRA Python Library

This library eases the use of the JIRA REST API from Python applications.

# Quickstart

Feeling impatient? I like your style.

    :::python
        from jira.client import JIRA

        options = { 'server': 'https://jira.atlassian.com'}
        jira = JIRA(options)

        issue = jira.issue('JRA-9')
        print issue.fields.project.key             # 'JRA'
        print issue.fields.issuetype.name          # 'New Feature'
        print issue.fields.reporter.displayName    # 'Mike Cannon-Brookes [Atlassian]'

# Getting Started

## Requirements

The library works off of Kenneth Reitz's indispensable [requests][1] library in addition to standard
pieces of the Python library. See `setup.py` for name and version details.

## Installation

Download and install using pip:

    pip install jira-python

You ARE using a [virtualenv][2], right?

# Usage

See the documentation for full details.

[1]: http://docs.python-requests.org/
[2]: http://www.virtualenv.org/en/latest/index.html