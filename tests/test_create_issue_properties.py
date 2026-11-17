from __future__ import annotations

import json
from unittest import mock

import pytest

from jira.client import JIRA

pytestmark = pytest.mark.unit

FIELDS = {
    "project": {"key": "TEST"},
    "issuetype": {"name": "Bug"},
    "summary": "Created with properties",
}


def _client() -> JIRA:
    client = JIRA.__new__(JIRA)
    client._options = {
        "server": "https://jira.example.com",
        "rest_path": "api",
        "rest_api_version": "2",
    }
    client._session = mock.Mock()
    response = mock.Mock(ok=True, status_code=201)
    response.json.return_value = {
        "id": "10000",
        "key": "TEST-1",
        "self": "https://jira.example.com/rest/api/2/issue/10000",
    }
    client._session.post.return_value = response
    return client


def _post_payload(client: JIRA) -> dict:
    assert client._session.post.call_count == 1
    kwargs = client._session.post.call_args.kwargs
    return json.loads(kwargs["data"])


def test_create_issue_includes_properties_with_fields_dict() -> None:
    client = _client()
    properties = [
        {"key": "build", "value": {"number": 42}},
        {"key": "source", "value": "api"},
    ]

    client.create_issue(fields=FIELDS.copy(), properties=properties, prefetch=False)

    payload = _post_payload(client)
    assert payload["fields"] == FIELDS
    assert payload["properties"] == properties


def test_create_issue_includes_properties_with_fieldargs() -> None:
    client = _client()
    properties = [{"key": "source", "value": "api"}]

    client.create_issue(
        project={"key": "TEST"},
        issuetype={"name": "Bug"},
        summary="Created with properties",
        properties=properties,
        prefetch=False,
    )

    payload = _post_payload(client)
    assert payload["fields"] == FIELDS
    assert payload["properties"] == properties


def test_create_issue_omits_properties_when_not_supplied() -> None:
    client = _client()

    client.create_issue(fields=FIELDS.copy(), prefetch=False)

    assert "properties" not in _post_payload(client)


def test_create_issue_preserves_empty_properties_list() -> None:
    client = _client()

    client.create_issue(fields=FIELDS.copy(), properties=[], prefetch=False)

    assert _post_payload(client)["properties"] == []


def test_create_issue_keeps_properties_field_separate() -> None:
    client = _client()
    fields = {**FIELDS, "properties": "field value"}
    properties = [{"key": "source", "value": "api"}]

    client.create_issue(fields=fields, properties=properties, prefetch=False)

    payload = _post_payload(client)
    assert payload["fields"]["properties"] == "field value"
    assert payload["properties"] == properties


def test_create_issue_properties_do_not_add_second_request() -> None:
    client = _client()
    prefetched = object()
    client.issue = mock.Mock(return_value=prefetched)  # type: ignore[method-assign]

    result = client.create_issue(
        fields=FIELDS.copy(),
        properties=[{"key": "source", "value": "api"}],
        prefetch=True,
    )

    assert result is prefetched
    assert client._session.post.call_count == 1
    client.issue.assert_called_once_with("TEST-1")  # type: ignore[attr-defined]
