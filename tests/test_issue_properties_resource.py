from unittest import mock

import pytest

from jira.resources import Issue

pytestmark = pytest.mark.unit


def test_issue_constructor_parses_top_level_properties() -> None:
    properties = [{"key": "source", "value": {"name": "api"}}]
    raw = {"id": "10000", "key": "TEST-1", "properties": properties}

    issue = Issue(
        {"server": "https://jira.example.com"},
        mock.Mock(),
        raw=raw,
    )

    assert issue.raw["properties"] == properties
    assert issue.properties[0].key == "source"
    assert issue.properties[0].value.name == "api"
