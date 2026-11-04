from __future__ import annotations

import os
import random
import string
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from jira import JIRA
from jira.resources import Issue, Project
from tests.conftest import api_probe_enabled

JSON_TYPES: dict[type, str] = {
    bool: "boolean",
    int: "integer",
    float: "number",
    str: "string",
    list: "array",
    dict: "object",
    type(None): "null",
}


@dataclass
class Observation:
    probe: str
    field: str
    expected: str
    observed: str


OBSERVATIONS: list[Observation] = []


def json_type(value: Any) -> str:
    return JSON_TYPES.get(type(value), type(value).__name__)


class Shape:
    """Records the JSON type of a field, then asserts it is the expected one."""

    def __init__(self, probe: str) -> None:
        self.probe = probe

    def __call__(self, field: str, value: Any, expected: str) -> None:
        observed = json_type(value)
        OBSERVATIONS.append(Observation(self.probe, field, expected, observed))
        assert observed == expected, f"{field}: expected {expected}, got {observed}"


@pytest.fixture
def shape(request: pytest.FixtureRequest) -> Shape:
    return Shape(request.node.name.removeprefix("test_"))


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    # pytest_ignore_collect only sees the directory; an explicit file path skips it.
    skip = pytest.mark.skip(reason="needs --run-api-probe or JIRA_API_PROBE=1")
    for item in items:
        if "api_probe" in item.path.parts:
            item.add_marker(pytest.mark.api_probe)
            if not api_probe_enabled(config):
                item.add_marker(skip)


def pytest_terminal_summary(terminalreporter: Any) -> None:
    if not OBSERVATIONS:
        return
    terminalreporter.section("api_probe observations")
    terminalreporter.write_line("| probe | field | expected | observed |")
    terminalreporter.write_line("|---|---|---|---|")
    for o in OBSERVATIONS:
        mark = "" if o.expected == o.observed else " **MISMATCH**"
        terminalreporter.write_line(
            f"| {o.probe} | `{o.field}` | {o.expected} | {o.observed}{mark} |"
        )


def unique_key(prefix: str = "PROBE") -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase, k=4))


@pytest.fixture(scope="session")
def jira_admin() -> JIRA:
    return JIRA(
        os.environ.get("CI_JIRA_URL", "http://localhost:2990/jira"),
        basic_auth=(
            os.environ.get("CI_JIRA_ADMIN", "admin"),
            os.environ.get("CI_JIRA_ADMIN_PASSWORD", "admin"),
        ),
    )


@pytest.fixture(scope="session")
def probe_project(jira_admin: JIRA) -> Iterator[Project]:
    key = unique_key()
    jira_admin.create_project(key, f"api probe {key}")
    try:
        yield jira_admin.project(key)
    finally:
        jira_admin.delete_project(key)


@pytest.fixture(scope="session")
def issue_types(probe_project: Project) -> dict[bool, str]:
    """Maps ``subtask`` to the name of one issue type of that kind."""
    by_kind: dict[bool, str] = {}
    for it in probe_project.raw["issueTypes"]:
        by_kind.setdefault(it["subtask"], it["name"])
    return by_kind


@pytest.fixture
def probe_issue(
    jira_admin: JIRA, probe_project: Project, issue_types: dict[bool, str]
) -> Iterator[Issue]:
    issue = jira_admin.create_issue(
        project=probe_project.key,
        summary="api probe",
        issuetype={"name": issue_types[False]},
    )
    try:
        yield issue
    finally:
        issue.delete(deleteSubtasks=True)
