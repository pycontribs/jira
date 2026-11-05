"""Static checks of decorated client signatures, enforced by the mypy run over tests/.

Every ``type: ignore[...]`` below is an assertion: with ``warn_unused_ignores``
mypy fails if that call stops being rejected.
"""

from __future__ import annotations

from typing import Any, assert_type

from requests import Response

from jira import JIRA
from jira.client import ResultList
from jira.resources import Comment, Dashboard, Issue, IssueLinkType, Project, Version


def _translate_resource_args_keeps_signature(
    j: JIRA, issue: Issue, project: Project, link_type: IssueLinkType
) -> None:
    assert_type(j.comments(issue), list[Comment])
    assert_type(j.comments("A-1"), list[Comment])
    assert_type(j.comments(10001), list[Comment])
    assert_type(j.project_versions(project), list[Version])
    assert_type(j.project_versions("PROJ"), list[Version])
    assert_type(j.create_issue_link(link_type, issue, "A-2"), Response)

    j.comments(1.5)  # type: ignore[arg-type]
    j.comments(issue, unknown_kwarg=1)  # type: ignore[call-arg]
    j.project_versions(issue)  # type: ignore[arg-type]
    j.add_worklog(issue, timeSpentSeconds=[3600])  # type: ignore[arg-type]


def _cloud_and_experimental_keep_signature(j: JIRA, flag: bool) -> None:
    assert_type(j.enhanced_search_issues("project = A"), ResultList[Issue] | None)
    assert_type(
        j.enhanced_search_issues("project = A", json_result=True),
        dict[str, Any] | None,
    )
    assert_type(
        j.enhanced_search_issues("project = A", json_result=flag),
        dict[str, Any] | ResultList[Issue] | None,
    )
    assert_type(j.approximate_issue_count("project = A"), int | None)
    assert_type(
        j.approximate_issue_count("project = A", json_result=True),
        dict[str, Any] | None,
    )
    assert_type(j.create_dashboard("name"), Dashboard | None)

    j.create_dashboard(42)  # type: ignore[arg-type]
    j.approximate_issue_count()  # type: ignore[call-overload]
