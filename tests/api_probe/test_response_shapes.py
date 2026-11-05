from __future__ import annotations

import pytest

from jira import JIRA
from jira.exceptions import JIRAError
from jira.resources import Issue, Project
from tests.api_probe.conftest import Shape, raw, unique_key


def test_transitions(jira_admin: JIRA, probe_issue: Issue, shape: Shape) -> None:
    transitions = jira_admin.transitions(probe_issue)
    shape("transitions[]", transitions, "array")
    first = transitions[0]
    shape("transitions[].id", first["id"], "string")
    shape("transitions[].to.id", first["to"]["id"], "string")

    expanded = jira_admin.transitions(probe_issue, expand="transitions.fields")
    shape("transitions[].fields (expand)", expanded[0]["fields"], "object")

    by_int_id = jira_admin.transitions(probe_issue, id=int(first["id"]))
    assert [t["id"] for t in by_int_id] == [first["id"]]

    found = jira_admin.find_transitionid_by_name(probe_issue, first["name"])
    shape("find_transitionid_by_name()", found, "string")

    # By name the client sends the id as a JSON string, by number as a JSON int.
    jira_admin.transition_issue(probe_issue, first["name"])
    again = jira_admin.transitions(probe_issue)[0]
    jira_admin.transition_issue(probe_issue, int(again["id"]))


def test_issue_id_and_key(
    jira_admin: JIRA, probe_issue: Issue, probe_project: Project, shape: Shape
) -> None:
    shape("issue.id", raw(probe_issue)["id"], "string")
    shape("issue.key", raw(probe_issue)["key"], "string")
    shape(
        "issue.fields.project.id", raw(probe_issue)["fields"]["project"]["id"], "string"
    )

    assert jira_admin.issue(int(probe_issue.id)).key == probe_issue.key

    result = jira_admin.search_issues(
        f"project = {probe_project.key}", maxResults=1, json_result=True
    )
    shape("search.total", result["total"], "integer")
    shape("search.startAt", result["startAt"], "integer")
    shape("search.issues[].id", result["issues"][0]["id"], "string")


def test_query_booleans(
    jira_admin: JIRA,
    probe_project: Project,
    issue_types: dict[bool, str],
) -> None:
    # requests renders Python bools as "True"/"False"; these show Jira accepts that.
    with pytest.raises(JIRAError) as exc:
        jira_admin.search_issues("nosuchfield = 1", validate_query=True)
    assert exc.value.status_code == 400
    lenient = jira_admin.search_issues(
        "nosuchfield = 1", validate_query=False, json_result=True
    )
    assert lenient["total"] == 0

    parent = jira_admin.create_issue(
        project=probe_project.key,
        summary="api probe parent",
        issuetype={"name": issue_types[False]},
    )
    deleted = False
    try:
        jira_admin.create_issue(
            project=probe_project.key,
            summary="api probe subtask",
            issuetype={"name": issue_types[True]},
            parent={"key": parent.key},
        )
        parent.delete(deleteSubtasks=True)
        deleted = True
    finally:
        if not deleted:
            jira_admin._session.delete(
                jira_admin._get_url(f"issue/{parent.key}"),
                params={"deleteSubtasks": "true"},
            )
    with pytest.raises(JIRAError) as gone:
        jira_admin.issue(parent.key)
    assert gone.value.status_code == 404


def test_project_id_and_key(
    jira_admin: JIRA, probe_project: Project, shape: Shape
) -> None:
    shape("project.id", raw(probe_project)["id"], "string")
    shape("project.key", raw(probe_project)["key"], "string")
    shape("project.issueTypes[]", raw(probe_project)["issueTypes"], "array")
    shape(
        "project.issueTypes[].subtask",
        raw(probe_project)["issueTypes"][0]["subtask"],
        "boolean",
    )

    assert jira_admin.project(int(probe_project.id)).key == probe_project.key
    roles = jira_admin.project_roles(int(probe_project.id))
    shape("project_roles()", roles, "object")
    role_id = next(iter(roles.values()))["id"]
    role = jira_admin.project_role(probe_project, int(role_id))
    shape("role.id", raw(role)["id"], "integer")


def test_version(jira_admin: JIRA, probe_project: Project, shape: Shape) -> None:
    version = jira_admin.create_version(unique_key("v"), probe_project.key)
    try:
        shape("version.id", raw(version)["id"], "string")
        shape("version.projectId", raw(version)["projectId"], "integer")
        shape("version.archived", raw(version)["archived"], "boolean")
        shape("version.released", raw(version)["released"], "boolean")

        vid = int(version.id)
        assert jira_admin.version(vid).id == version.id
        counts = jira_admin.version_count_related_issues(vid)
        shape(
            "relatedIssueCounts.issuesFixedCount", counts["issuesFixedCount"], "integer"
        )
        unresolved = jira_admin.version_count_unresolved_issues(vid)
        shape("unresolvedIssueCount.issuesUnresolvedCount", unresolved, "integer")
        moved = jira_admin.move_version(vid, position="First")
        shape("move_version().id", raw(moved)["id"], "string")
        listed = jira_admin.project_versions(int(probe_project.id))
        assert version.id in [v.id for v in listed]
    finally:
        version.delete()


def test_component(jira_admin: JIRA, probe_project: Project, shape: Shape) -> None:
    component = jira_admin.create_component(unique_key("c"), probe_project.key)
    try:
        shape("component.id", raw(component)["id"], "string")
        shape("component.projectId", raw(component)["projectId"], "integer")
        shape("component.project", raw(component)["project"], "string")
        shape(
            "component.isAssigneeTypeValid",
            raw(component)["isAssigneeTypeValid"],
            "boolean",
        )

        cid = int(component.id)
        assert jira_admin.component(cid).id == component.id
        count = jira_admin.component_count_related_issues(cid)
        shape("component relatedIssueCounts.issueCount", count, "integer")
        listed = jira_admin.project_components(int(probe_project.id))
        assert component.id in [c.id for c in listed]
    finally:
        component.delete()


def test_filter(jira_admin: JIRA, probe_project: Project, shape: Shape) -> None:
    created = jira_admin.create_filter(
        name=unique_key("f"), jql=f"project = {probe_project.key}", favourite=False
    )
    try:
        shape("filter.id", raw(created)["id"], "string")
        shape("filter.favourite", raw(created)["favourite"], "boolean")

        fid = int(created.id)
        assert jira_admin.filter(fid).id == created.id
        updated = jira_admin.update_filter(fid, name=unique_key("f"))
        shape("update_filter().id", raw(updated)["id"], "string")
    finally:
        created.delete()


def test_board_and_sprint(
    jira_admin: JIRA, probe_project: Project, shape: Shape
) -> None:
    created = jira_admin.create_filter(
        name=unique_key("f"), jql=f"project = {probe_project.key}", favourite=False
    )
    boards = []
    try:
        # The agile spec types filterId as int64; Server takes either.
        for filter_id in (int(created.id), str(created.id)):
            board = jira_admin.create_board(unique_key("b"), filter_id)
            boards.append(board)
            shape(
                f"board.id (filter_id {type(filter_id).__name__})",
                raw(board)["id"],
                "integer",
            )

        listed = jira_admin.boards(projectKeyOrID=probe_project.key)
        assert boards[0].id in [b.id for b in listed]
        listed_by_obj = jira_admin.boards(projectKeyOrID=probe_project)
        assert [b.id for b in listed_by_obj] == [b.id for b in listed]

        sprint = jira_admin.create_sprint(unique_key("s"), boards[0].id)
        try:
            shape("sprint.id", raw(sprint)["id"], "integer")
            shape("sprint.originBoardId", raw(sprint)["originBoardId"], "integer")
            shape("sprint.state", raw(sprint)["state"], "string")
            assert jira_admin.sprint(str(sprint.id)).id == sprint.id
            sprints = jira_admin.sprints(str(boards[0].id))
            shape("sprints[].id", raw(sprints[0])["id"], "integer")
        finally:
            sprint.delete()
    finally:
        for board in boards:
            board.delete()
        created.delete()


def test_worklog(jira_admin: JIRA, probe_issue: Issue, shape: Shape) -> None:
    for seconds in (3600, "3600"):
        worklog = jira_admin.add_worklog(probe_issue, timeSpentSeconds=seconds)
        label = type(seconds).__name__
        shape(f"worklog.id (sent {label})", raw(worklog)["id"], "string")
        shape(f"worklog.issueId (sent {label})", raw(worklog)["issueId"], "string")
        shape(
            f"worklog.timeSpentSeconds (sent {label})",
            raw(worklog)["timeSpentSeconds"],
            "integer",
        )
    assert len(jira_admin.worklogs(probe_issue)) == 2


def test_my_permissions(
    jira_admin: JIRA, probe_project: Project, probe_issue: Issue, shape: Shape
) -> None:
    variants = {
        "projectKey": jira_admin.my_permissions(projectKey=probe_project.key),
        "projectId int": jira_admin.my_permissions(projectId=int(probe_project.id)),
        "issueId int": jira_admin.my_permissions(issueId=int(probe_issue.id)),
    }
    for label, result in variants.items():
        perm = result["permissions"]["BROWSE_PROJECTS"]
        shape(
            f"permissions.*.havePermission ({label})", perm["havePermission"], "boolean"
        )
        shape(f"permissions.*.id ({label})", perm["id"], "string")
    with_deprecated = [
        p
        for p in variants["projectKey"]["permissions"].values()
        if "deprecatedKey" in p
    ]
    if with_deprecated:
        shape(
            "permissions.*.deprecatedKey",
            with_deprecated[0]["deprecatedKey"],
            "boolean",
        )


def test_application_properties(jira_admin: JIRA, shape: Shape) -> None:
    props = jira_admin.application_properties()
    shape("application_properties()", props, "array")
    assert isinstance(props, list)
    first = props[0]
    shape("application_properties()[].id", first["id"], "string")
    shape("application_properties()[].value", first["value"], "string")
    with_allowed = [p for p in props if "allowedValues" in p]
    if with_allowed:
        shape(
            "application_properties()[].allowedValues",
            with_allowed[0]["allowedValues"],
            "array",
        )

    single = jira_admin.application_properties(key="jira.title")
    shape("application_properties(key)", single, "object")


def test_attachment_meta(jira_admin: JIRA, shape: Shape) -> None:
    meta = jira_admin.attachment_meta()
    shape("attachment/meta.enabled", meta["enabled"], "boolean")
    shape("attachment/meta.uploadLimit", meta["uploadLimit"], "integer")
