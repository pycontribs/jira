"""Opt-in probes of live Jira response shapes.

These create and delete data on ``CI_JIRA_URL`` and are never collected unless
``--run-api-probe`` or ``JIRA_API_PROBE=1`` is given::

    JIRA_API_PROBE=1 pytest tests/api_probe -p no:cacheprovider

Each probe asserts the JSON type of the fields the client's annotations rely on,
and the session ends with a table of what was observed.
"""
