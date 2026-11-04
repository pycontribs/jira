"""Offline checks that a Resource argument and its key send the same request.

Every method decorated with ``translate_resource_args`` is covered: the cases
are keyed by (method, parameter) pairs read off the annotations, so a new
decorated method or a new Resource-typed parameter fails the coverage test
until it gets a case here.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any, get_type_hints

import pytest
import requests_mock as rm

import jira.client
from jira.resources import Issue, IssueLinkType, Project, Resource

SERVER = "https://jira.example.com"
API = f"{SERVER}/rest/api/2"
AGILE = f"{SERVER}/rest/agile/1.0"

TRANSLATED = (Issue, Project, IssueLinkType)

LINK_TYPE_RAW = {
    "id": "1",
    "name": "Blocks",
    "inward": "is blocked by",
    "outward": "blocks",
}

# Decorated methods with no parameter that accepts an Issue, Project or
# IssueLinkType, so there is nothing for the decorator to pass through.
NO_RESOURCE_PARAMETER = {
    "add_comment_property",
    "comment_properties",
    "comment_property",
    "sprints",
}

Responses = list[tuple[str, str, dict[str, Any]]]

USER_SEARCH: Responses = [
    (
        "GET",
        f"{API}/user/search",
        {"json": [{"name": "bob", "key": "bob", "self": f"{API}/user?username=bob"}]},
    )
]

# method -> (arguments by name with every Resource given as its key or name,
# extra responses as (HTTP method, URL, register_uri kwargs)). Requests that
# match none of the extra responses get ``{"id": "1"}``.
CASES: dict[str, tuple[dict[str, Any], Responses]] = {
    "add_attachment": (
        {"issue": "ABC-1", "attachment": b"content", "filename": "a.txt"},
        [
            (
                "POST",
                f"{API}/issue/ABC-1/attachments",
                {"json": [{"id": "1", "size": 7}]},
            )
        ],
    ),
    "add_comment": ({"issue": "ABC-1", "body": "hello"}, []),
    "add_issue_property": ({"issue": "ABC-1", "key": "k", "data": {"a": 1}}, []),
    "add_vote": ({"issue": "ABC-1"}, []),
    "add_watcher": ({"issue": "ABC-1", "watcher": "bob"}, USER_SEARCH),
    "add_worklog": ({"issue": "ABC-1", "timeSpent": "1h"}, []),
    "assign_issue": ({"issue": "ABC-1", "assignee": "bob"}, USER_SEARCH),
    "boards": (
        {"projectKeyOrID": "PROJ"},
        [("GET", f"{AGILE}/board", {"json": {"values": [], "isLast": True}})],
    ),
    "comment": ({"issue": "ABC-1", "comment": "1"}, []),
    "comments": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/comment", {"json": {"comments": []}})],
    ),
    "confirm_project_avatar": (
        {"project": "PROJ", "cropping_properties": {"cropperWidth": 1}},
        [],
    ),
    "create_component": ({"name": "c", "project": "PROJ"}, []),
    "create_issue_link": (
        {"type": "Blocks", "inwardIssue": "ABC-1", "outwardIssue": "ABC-2"},
        [
            (
                "GET",
                f"{API}/issueLinkType",
                {"json": {"issueLinkTypes": [LINK_TYPE_RAW]}},
            )
        ],
    ),
    "create_temp_project_avatar": (
        {
            "project": "PROJ",
            "filename": __file__,
            "size": 0,
            "avatar_img": b"png",
            "contentType": "image/png",
        },
        [],
    ),
    "create_version": ({"name": "1.0", "project": "PROJ"}, []),
    "delete_project_avatar": ({"project": "PROJ", "avatar": "10"}, []),
    "delete_remote_link": ({"issue": "ABC-1", "internal_id": "1"}, []),
    "editmeta": ({"issue": "ABC-1"}, []),
    "get_project_version_by_name": (
        {"project": "PROJ", "version_name": "1.0"},
        [("GET", f"{API}/project/PROJ/versions", {"json": []})],
    ),
    "issue_properties": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/properties", {"json": {"keys": []}})],
    ),
    "issue_property": ({"issue": "ABC-1", "key": "k"}, []),
    "pin_comment": ({"issue": "ABC-1", "comment": "1", "pin": True}, []),
    "pinned_comments": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/pinned-comments", {"json": []})],
    ),
    "project_avatars": ({"project": "PROJ"}, []),
    "project_components": (
        {"project": "PROJ"},
        [("GET", f"{API}/project/PROJ/components", {"json": []})],
    ),
    "project_issue_security_level_scheme": ({"project": "PROJ"}, []),
    "project_notification_scheme": ({"project": "PROJ"}, []),
    "project_permissionscheme": ({"project": "PROJ"}, []),
    "project_priority_scheme": ({"project": "PROJ"}, []),
    "project_role": ({"project": "PROJ", "id": "10002"}, []),
    "project_roles": ({"project": "PROJ"}, []),
    "project_securitylevels": (
        {"project": "PROJ"},
        [("GET", f"{API}/project/PROJ/securitylevel", {"json": {"levels": []}})],
    ),
    "project_versions": (
        {"project": "PROJ"},
        [("GET", f"{API}/project/PROJ/versions", {"json": []})],
    ),
    "project_workflow_scheme": ({"project": "PROJ"}, []),
    "remote_link": ({"issue": "ABC-1", "id": "1"}, []),
    "remote_links": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/remotelink", {"json": []})],
    ),
    "remove_vote": ({"issue": "ABC-1"}, []),
    "remove_watcher": ({"issue": "ABC-1", "watcher": "bob"}, USER_SEARCH),
    "rename_version": (
        {"project": "PROJ", "old_name": "1.0", "new_name": "2.0"},
        [("GET", f"{API}/project/PROJ/versions", {"json": []})],
    ),
    "set_project_avatar": ({"project": "PROJ", "avatar": "10"}, []),
    "transition_issue": ({"issue": "ABC-1", "transition": "11"}, []),
    "transitions": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/transitions", {"json": {"transitions": []}})],
    ),
    "votes": ({"issue": "ABC-1"}, []),
    "watchers": ({"issue": "ABC-1"}, []),
    "worklog": ({"issue": "ABC-1", "id": "1"}, []),
    "worklogs": (
        {"issue": "ABC-1"},
        [("GET", f"{API}/issue/ABC-1/worklog", {"json": {"worklogs": []}})],
    ),
}


def _is_translated(method: Callable[..., Any]) -> bool:
    wrapper_code = jira.client.translate_resource_args(lambda: None).__code__
    layer: Any = method
    while layer is not None:
        if getattr(layer, "__code__", None) is wrapper_code:
            return True
        layer = getattr(layer, "__wrapped__", None)
    return False


def _translated_classes(annotation: Any) -> tuple[type[Resource], ...]:
    return tuple(
        c for c in getattr(annotation, "__args__", (annotation,)) if c in TRANSLATED
    )


def _decorated_methods() -> list[str]:
    return sorted(
        name
        for name, member in vars(jira.client.JIRA).items()
        if callable(member) and _is_translated(member)
    )


def _resource_parameters() -> list[tuple[str, str, type[Resource]]]:
    pairs = []
    for name in _decorated_methods():
        hints = get_type_hints(inspect.unwrap(getattr(jira.client.JIRA, name)))
        for param, hint in hints.items():
            classes = _translated_classes(hint)
            if param != "return" and classes:
                assert len(classes) == 1, (name, param, classes)
                pairs.append((name, param, classes[0]))
    return pairs


RESOURCE_PARAMETERS = _resource_parameters()


def _resource(client: jira.client.JIRA, cls: type[Resource], key: str) -> Resource:
    options, session = client._options, client._session
    if cls is IssueLinkType:
        assert key == LINK_TYPE_RAW["name"]
        return IssueLinkType(options, session, raw=dict(LINK_TYPE_RAW))
    if cls is Issue:
        return Issue(options, session, raw={"id": "10001", "key": key})
    assert cls is Project
    return Project(options, session, raw={"id": "10000", "key": key})


def _positional(
    method: Callable[..., Any], kwargs: dict[str, Any], up_to: str
) -> tuple[list[Any], dict[str, Any]]:
    """Move ``up_to`` and every parameter before it into positional arguments."""
    params = list(inspect.signature(method).parameters.values())
    args = []
    rest = dict(kwargs)
    for p in params:
        args.append(rest.pop(p.name) if p.name in rest else p.default)
        if p.name == up_to:
            return args, rest
    raise AssertionError(f"{up_to} is not a parameter of {method.__name__}")


def _body(request: Any) -> bytes:
    body = request.body
    if hasattr(body, "read"):
        body = body.read()
    if body is None:
        return b""
    if isinstance(body, str):
        body = body.encode()
    boundary = re.search(r"boundary=(\S+)", request.headers.get("Content-Type", ""))
    if boundary:
        body = body.replace(boundary.group(1).encode(), b"BOUNDARY")
    return body


def test_every_resource_parameter_has_a_case():
    decorated = set(_decorated_methods())
    with_resource = {name for name, _, _ in RESOURCE_PARAMETERS}

    assert decorated == set(CASES) | NO_RESOURCE_PARAMETER
    assert with_resource == set(CASES)
    assert not with_resource & NO_RESOURCE_PARAMETER


@pytest.mark.parametrize(
    ("method_name", "param", "cls"),
    [pytest.param(*pair, id=f"{pair[0]}-{pair[1]}") for pair in RESOURCE_PARAMETERS],
)
def test_resource_and_its_key_send_the_same_request(
    requests_mock, method_name, param, cls
):
    client = jira.client.JIRA(server=SERVER, get_server_info=False, validate=False)
    kwargs, responses = CASES[method_name]
    requests_mock.register_uri(rm.ANY, rm.ANY, json={"id": "1"})
    for http_method, url, response in responses:
        requests_mock.register_uri(http_method, url, **response)
    method = getattr(client, method_name)
    resource = _resource(client, cls, kwargs[param])

    def sent(
        args: list[Any], call_kwargs: dict[str, Any]
    ) -> list[tuple[str, str, bytes]]:
        start = len(requests_mock.request_history)
        method(*args, **call_kwargs)
        return [
            (r.method, r.url, _body(r)) for r in requests_mock.request_history[start:]
        ]

    by_key = sent(*_positional(method, kwargs, param))
    args, rest = _positional(method, {**kwargs, param: resource}, param)
    positional = sent(args, rest)
    keyword = sent([], {**kwargs, param: resource})

    assert by_key
    assert positional == by_key
    assert keyword == by_key
