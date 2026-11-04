from __future__ import annotations

import copy
import functools
import getpass
import inspect
import io
import json
import logging
import sys
import types
from typing import Any
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
import requests.sessions
import requests_mock as rm

import jira.client
from jira.client import JIRA
from jira.exceptions import JIRAError, NotJIRAInstanceError
from jira.resources import (
    Issue,
    IssueLinkType,
    Project,
    Resource,
    SecurityLevel,
    Version,
)
from tests.conftest import JiraTestManager, allow_on_cloud, get_unique_project_name


@pytest.fixture()
def prep():
    pass


@pytest.fixture(scope="module")
def test_manager() -> JiraTestManager:
    return JiraTestManager()


@pytest.fixture()
def cl_admin(test_manager: JiraTestManager) -> jira.client.JIRA:
    return test_manager.jira_admin


@pytest.fixture()
def cl_normal(test_manager: JiraTestManager) -> jira.client.JIRA:
    return test_manager.jira_normal


@pytest.fixture(scope="function")
def slug(request: pytest.FixtureRequest, cl_admin: jira.client.JIRA):
    """Project slug."""
    slug = get_unique_project_name()
    project_name = f"Test user={getpass.getuser()} key={slug} A"

    proj: Project | dict[str, Any]
    try:
        proj = cl_admin.project(slug)
    except JIRAError:
        proj = cl_admin.create_project(slug, project_name)
    assert proj

    yield slug
    try:
        cl_admin.delete_project(slug, enable_undo=False)
    except (ValueError, JIRAError):
        # Some tests have project already removed, so we stay silent
        pass


@pytest.fixture(scope="session")
def stream_logger():
    logger = logging.getLogger("test_logger")
    logger.addHandler(logging.StreamHandler())
    return logger


@pytest.fixture(scope="session")
def mock_not_jira_client(stream_logger):
    class MockClient:
        def __init__(self, is_cloud=False):
            self.is_cloud = is_cloud
            self.log = stream_logger

        @property
        def _is_cloud(self):
            return self.is_cloud

        @jira.client.cloud_api
        def mock_cloud_only_method(self, *args, **kwargs):
            return args, kwargs

        @jira.client.experimental_atlassian_api
        def mock_experimental_method(self, *args, **kwargs):
            return args, kwargs

        @jira.client.experimental_atlassian_api
        def mock_method_raises_jira_error(self, *args, **kwargs):
            raise JIRAError(**kwargs)

    return MockClient


@pytest.fixture(scope="session")
def mock_jira_client(stream_logger):
    class MockClient(jira.client.JIRA):
        def __init__(self, is_cloud=False):
            self.is_cloud = is_cloud
            self.log = stream_logger

        @property
        def _is_cloud(self):
            return self.is_cloud

        @jira.client.cloud_api
        def mock_cloud_only_method(self, *args, **kwargs):
            return args, kwargs

        @jira.client.experimental_atlassian_api
        def mock_experimental_method(self, *args, **kwargs):
            return args, kwargs

        @jira.client.experimental_atlassian_api
        def mock_method_raises_jira_error(self, *args, **kwargs):
            raise JIRAError(**kwargs)

    return MockClient


@pytest.fixture(scope="session")
def mock_response():
    class MockResponse:
        def __init__(self, status_code=404):
            self.status_code = status_code
            self.url = "some/url/that/does/not/exist"

    return MockResponse


@allow_on_cloud
def test_delete_project(cl_admin, cl_normal, slug):
    assert cl_admin.delete_project(slug)


@allow_on_cloud
def test_delete_inexistent_project(cl_admin):
    # cspell:ignore abogus123
    slug = "abogus123"
    with pytest.raises(JIRAError) as ex:
        assert cl_admin.delete_project(slug)

    assert "No project could be found with key" in str(
        ex.value
    ) or f'Parameter pid="{slug}" is not a Project, projectID or slug' in str(ex.value)


def test_templates(cl_admin):
    templates = set(cl_admin.templates())
    expected_templates = set(
        filter(
            None,
            """
Basic software development
Kanban software development
Process management
Project management
Scrum software development
Task management
""".split("\n"),
        )
    )

    assert templates == expected_templates


@allow_on_cloud
def test_result_list():
    iterable = [2, 3]
    startAt = 0
    maxResults = 50
    total = 2

    results = jira.client.ResultList(iterable, startAt, maxResults, total)

    for idx, result in enumerate(results):
        assert results[idx] == iterable[idx]

    assert next(results) == iterable[0]
    assert next(results) == iterable[1]

    with pytest.raises(StopIteration):
        next(results)


@allow_on_cloud
def test_result_list_if_empty():
    results = jira.client.ResultList()

    for r in results:
        raise AssertionError("`results` should be empty")

    with pytest.raises(StopIteration):
        next(results)


@pytest.mark.parametrize(
    ("args", "kwargs", "expected_params"),
    [
        (
            ("legacy-user", "PROJ,OPS"),
            {},
            {"username": "legacy-user", "projectKeys": "PROJ,OPS"},
        ),
        (
            (),
            {"accountId": "123:abc", "projectKeys": "PROJ,OPS"},
            {"accountId": "123:abc", "projectKeys": "PROJ,OPS"},
        ),
    ],
    ids=["legacy-positional-username", "cloud-account-id"],
)
def test_search_assignable_users_for_projects_parameters(args, kwargs, expected_params):
    client = jira.client.JIRA(
        server="https://example.atlassian.net",
        get_server_info=False,
        validate=False,
    )
    with mock.patch.object(client, "_fetch_pages", return_value=[]) as fetch_pages:
        result = client.search_assignable_users_for_projects(
            *args, startAt=2, maxResults=7, **kwargs
        )

    assert result == []
    fetch_pages.assert_called_once_with(
        jira.client.User,
        None,
        "user/assignable/multiProjectSearch",
        2,
        7,
        expected_params,
    )


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"accountId": "123:abc"}, TypeError, "projectKeys"),
        ({"projectKeys": "PROJ"}, ValueError, "exactly one"),
        (
            {"username": "legacy-user", "accountId": "123:abc", "projectKeys": "PROJ"},
            ValueError,
            "exactly one",
        ),
    ],
)
def test_search_assignable_users_for_projects_invalid_arguments(kwargs, error, message):
    client = jira.client.JIRA(
        server="https://example.atlassian.net",
        get_server_info=False,
        validate=False,
    )
    with mock.patch.object(client, "_fetch_pages") as fetch_pages:
        with pytest.raises(error, match=message):
            client.search_assignable_users_for_projects(**kwargs)
    fetch_pages.assert_not_called()


@allow_on_cloud
@pytest.mark.parametrize(
    "options_arg",
    [
        {"headers": {"Content-Type": "application/json;charset=UTF-8"}},
        {"headers": {"random-header": "nice random"}},
    ],
    ids=["overwrite", "new"],
)
def test_headers_unclobbered_update(options_arg, no_fields):
    assert "headers" in options_arg, "test case options must contain headers"

    # GIVEN: the headers and the expected value
    header_to_check: str = list(options_arg["headers"].keys())[0]
    expected_header_value: str = options_arg["headers"][header_to_check]

    invariant_header_name: str = "X-Atlassian-Token"
    invariant_header_value: str = jira.client.JIRA.DEFAULT_OPTIONS["headers"][
        invariant_header_name
    ]

    # We arbitrarily chose a header to check it remains unchanged/unclobbered
    # so should not be overwritten by a test case
    assert invariant_header_name not in options_arg["headers"], (
        f"{invariant_header_name} is checked as not being overwritten in this test"
    )

    # WHEN: we initialise the JIRA class and get the headers
    jira_client = jira.client.JIRA(
        server="https://jira.atlasian.com",
        get_server_info=False,
        validate=False,
        options=options_arg,
    )

    session_headers = jira_client._session.headers

    # THEN: we have set the right headers and not affect the other headers' defaults
    assert session_headers[header_to_check] == expected_header_value
    assert session_headers[invariant_header_name] == invariant_header_value


@allow_on_cloud
def test_headers_unclobbered_update_with_no_provided_headers(no_fields):
    options_arg = {}  # a dict with "headers" not set

    # GIVEN:the headers and the expected value
    invariant_header_name: str = "X-Atlassian-Token"
    invariant_header_value: str = jira.client.JIRA.DEFAULT_OPTIONS["headers"][
        invariant_header_name
    ]

    # WHEN: we initialise the JIRA class with no provided headers and get the headers
    jira_client = jira.client.JIRA(
        server="https://jira.atlasian.com",
        get_server_info=False,
        validate=False,
        options=options_arg,
    )

    session_headers = jira_client._session.headers

    # THEN: we have not affected the other headers' defaults
    assert session_headers[invariant_header_name] == invariant_header_value


def test_token_auth(cl_admin: jira.client.JIRA):
    """Tests the Personal Access Token authentication works."""
    # GIVEN: We have a PAT token created by a user.
    pat_token_request = {
        "name": "my_new_token",
        "expirationDuration": 1,
    }
    base_url = cl_admin.server_url
    pat_token_response = cl_admin._session.post(
        f"{base_url}/rest/pat/latest/tokens", json=pat_token_request
    ).json()
    new_token = pat_token_response["rawToken"]

    # WHEN: A new client is authenticated with this token
    new_jira_client = jira.client.JIRA(server=base_url, token_auth=new_token)

    # THEN: The reported authenticated user of the token
    # matches the original token creator user.
    assert cl_admin.myself() == new_jira_client.myself()


def test_bearer_token_auth():
    my_token = "cool-token"
    token_auth_jira = jira.client.JIRA(
        server="https://what.ever",
        token_auth=my_token,
        get_server_info=False,
        validate=False,
    )
    method_send = token_auth_jira._session.send
    with mock.patch.object(token_auth_jira._session, method_send.__name__) as mock_send:
        token_auth_jira._session.get(token_auth_jira.server_url)
        prepared_req: requests.sessions.PreparedRequest = mock_send.call_args[0][0]
        assert prepared_req.headers["Authorization"] == f"Bearer {my_token}"


def test_cookie_auth(test_manager: JiraTestManager):
    """Test Cookie based authentication works.

    NOTE: this is deprecated in Cloud and is not recommended in Server.
    https://developer.atlassian.com/cloud/jira/platform/jira-rest-api-cookie-based-authentication/
    https://developer.atlassian.com/server/jira/platform/cookie-based-authentication/
    """
    # GIVEN: the username and password
    # WHEN: We create a session with cookie auth for the same server
    cookie_auth_jira = jira.client.JIRA(
        server=test_manager.CI_JIRA_URL,
        auth=(test_manager.CI_JIRA_ADMIN, test_manager.CI_JIRA_ADMIN_PASSWORD),
    )
    # THEN: We get the same result from the API
    assert test_manager.jira_admin.myself() == cookie_auth_jira.myself()


def test_cookie_auth_retry(requests_mock):
    """Test Cookie based authentication retry logic works."""
    # GIVEN: a mocked Jira that always returns 401 on the auth URL
    auth_class = jira.client.JiraCookieAuth
    reset_func = jira.client.JiraCookieAuth._reset_401_retry_counter
    new_options = jira.client.JIRA.DEFAULT_OPTIONS.copy()
    new_options["auth_url"] = "/401"
    requests_mock.register_uri(
        rm.ANY,
        "https://mocked.jira.invalid/401",
        status_code=401,
    )
    with pytest.raises(JIRAError):
        with mock.patch.object(auth_class, reset_func.__name__) as mock_reset_func:
            # WHEN: We create a session with cookie auth
            jira.client.JIRA(
                server="https://mocked.jira.invalid",
                options=new_options,
                auth=("user", "pass"),
            )
    # THEN: We don't get a RecursionError and only call the reset_function once
    mock_reset_func.assert_called_once()


def test_createmeta_issuetypes_pagination(cl_normal, slug):
    """Test createmeta_issuetypes pagination kwargs"""
    issue_types_resp = cl_normal.createmeta_issuetypes(slug, startAt=50, maxResults=100)
    assert issue_types_resp["startAt"] == 50
    assert issue_types_resp["maxResults"] == 100


def test_createmeta_fieldtypes_pagination(cl_normal, slug):
    """Test createmeta_fieldtypes pagination kwargs"""
    issue_types = cl_normal.createmeta_issuetypes(slug)
    assert issue_types["total"]
    issue_type_id = issue_types["values"][-1]["id"]
    field_types_resp = cl_normal.createmeta_fieldtypes(
        projectIdOrKey=slug, issueTypeId=issue_type_id, startAt=50, maxResults=100
    )
    assert field_types_resp["startAt"] == 50
    assert field_types_resp["maxResults"] == 100


def _createmeta_client(deployment_type: str, version: tuple[int, ...]):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client.deploymentType = deployment_type
    client._version = version
    return client


@pytest.mark.parametrize(
    "deployment_type,version,items_key",
    [("Cloud", (1001, 0, 0), "issueTypes"), ("Server", (9, 12, 0), "values")],
)
def test_project_issue_types(requests_mock, deployment_type, version, items_key):
    client = _createmeta_client(deployment_type, version)
    requests_mock.get(
        "https://jira.example.com/rest/api/2/issue/createmeta/ABC/issuetypes",
        json={
            "startAt": 0,
            "maxResults": 50,
            "total": 2,
            items_key: [{"id": "1", "name": "Bug"}, {"id": "2", "name": "Task"}],
        },
    )

    issue_types = client.project_issue_types("ABC")

    assert [it.name for it in issue_types] == ["Bug", "Task"]


@pytest.mark.parametrize(
    "deployment_type,version,items_key",
    [("Cloud", (1001, 0, 0), "fields"), ("Server", (9, 12, 0), "values")],
)
def test_project_issue_fields(requests_mock, deployment_type, version, items_key):
    client = _createmeta_client(deployment_type, version)
    requests_mock.get(
        "https://jira.example.com/rest/api/2/issue/createmeta/ABC/issuetypes/1",
        json={
            "startAt": 0,
            "maxResults": 50,
            "total": 2,
            items_key: [
                {"fieldId": "summary", "name": "Summary", "required": True},
                {"fieldId": "assignee", "name": "Assignee", "required": False},
            ],
        },
    )

    fields = client.project_issue_fields("ABC", "1")

    assert [f.fieldId for f in fields] == ["summary", "assignee"]


def test_project_issue_types_refused_before_server_8_4(requests_mock):
    client = _createmeta_client("Server", (8, 3, 0))

    with pytest.raises(JIRAError, match="Requires Server/DC 8.4"):
        client.project_issue_types("ABC")

    assert not requests_mock.called


@pytest.mark.parametrize(
    "mock_client_method", ["mock_cloud_only_method", "mock_experimental_method"]
)
def test_not_cloud_instance(mock_not_jira_client, mock_client_method):
    client = mock_not_jira_client()
    with pytest.raises(NotJIRAInstanceError) as exc:
        getattr(client, mock_client_method)()

    assert str(exc.value) == (
        "The first argument of this function must be an instance of type "
        f"JIRA. Instance Type: {mock_not_jira_client().__class__.__name__}"
    )


@mock.patch("requests.Session.request")
def test_cloud_api(mock_request, mock_jira_client):
    mock_client = mock_jira_client(is_cloud=True)
    out = mock_client.mock_cloud_only_method("one", two="three")
    assert out is not None


@mock.patch("requests.Session.request")
def test_cloud_api_not_cloud_server(mock_request, mock_jira_client, caplog):
    mock_client = mock_jira_client()
    mock_client.mock_cloud_only_method()
    assert caplog.messages[0] == (
        "This functionality is not available on Jira Data Center (Server) version."
    )


@pytest.mark.parametrize(
    "account_id",
    ["5b10ac8d82e05b22cc7d4ef5", "712020:c3eb69e6-897e-4578-a9f5-8d42fd5e948d"],
)
def test_get_user_id_keeps_cloud_account_id(mock_jira_client, account_id):
    """An account id needs no user search, which requires the Browse users permission."""
    client = mock_jira_client(is_cloud=True)
    with mock.patch.object(jira.client.JIRA, "search_users") as mock_search_users:
        assert client._get_user_id(account_id) == account_id

    mock_search_users.assert_not_called()


def test_get_user_id_searches_for_other_values(mock_jira_client):
    client = mock_jira_client(is_cloud=True)
    user = mock.Mock(accountId="5b10ac8d82e05b22cc7d4ef5")
    with mock.patch.object(
        jira.client.JIRA, "search_users", return_value=[user]
    ) as mock_search_users:
        assert client._get_user_id("user@example.com") == "5b10ac8d82e05b22cc7d4ef5"

    mock_search_users.assert_called_once_with(query="user@example.com", maxResults=20)


def test_get_user_id_searches_for_account_id_shaped_name_on_server(mock_jira_client):
    """Self hosted instances identify users by name, so the search is kept."""
    client = mock_jira_client()
    user = mock.Mock(name_="username")
    user.name = "username"
    with mock.patch.object(
        jira.client.JIRA, "search_users", return_value=[user]
    ) as mock_search_users:
        assert client._get_user_id("5b10ac8d82e05b22cc7d4ef5") == "username"

    mock_search_users.assert_called_once_with(
        user="5b10ac8d82e05b22cc7d4ef5", maxResults=20
    )


def test_add_watcher_posts_cloud_account_id_without_user_search(mock_jira_client):
    """Adding a watcher by account id must not need the Browse users permission."""
    account_id = "5b10ac8d82e05b22cc7d4ef5"
    url = "https://example.atlassian.net/rest/api/2/issue/TEST-1/watchers"
    client = mock_jira_client(is_cloud=True)
    client._session = mock.Mock()
    with (
        mock.patch.object(jira.client.JIRA, "search_users") as mock_search_users,
        mock.patch.object(jira.client.JIRA, "_get_url", return_value=url),
    ):
        client.add_watcher("TEST-1", account_id)

    mock_search_users.assert_not_called()
    client._session.post.assert_called_once_with(url, data=json.dumps(account_id))


def _group_user(name: str) -> dict:
    return {"name": name, "displayName": name.title(), "active": True}


def test_group_members_expands_users_before_jira_10(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client._version = (9, 12, 0)
    url = "https://jira.example.com/rest/api/2/group"
    requests_mock.get(
        url,
        [
            {
                "json": {
                    "users": {
                        "size": 3,
                        "end-index": 1,
                        "items": [_group_user("alice"), _group_user("bob")],
                    }
                }
            },
            {
                "json": {
                    "users": {
                        "size": 3,
                        "end-index": 2,
                        "items": [_group_user("carol")],
                    }
                }
            },
        ],
    )

    members = client.group_members("devs")

    assert list(members) == ["alice", "bob", "carol"]
    assert [r.qs["expand"] for r in requests_mock.request_history] == [
        ["users"],
        ["users[2:51]"],
    ]


def test_group_members_pages_group_member_on_jira_10(requests_mock):
    """Regression test for https://github.com/pycontribs/jira/issues/891."""
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    client._version = (10, 3, 7)
    url = "https://jira.example.com/rest/api/2/group/member"
    requests_mock.get(
        url,
        [
            {
                "json": {
                    "startAt": 0,
                    "maxResults": 2,
                    "isLast": False,
                    "values": [_group_user("alice"), _group_user("bob")],
                }
            },
            {
                "json": {
                    "startAt": 2,
                    "maxResults": 2,
                    "isLast": True,
                    "values": [_group_user("carol")],
                }
            },
        ],
    )

    members = client.group_members("devs")

    assert list(members) == ["alice", "bob", "carol"]
    history = requests_mock.request_history
    assert all(r.path == "/rest/api/2/group/member" for r in history)
    assert [parse_qs(urlsplit(r.url).query) for r in history] == [
        {"groupname": ["devs"]},
        {"groupname": ["devs"], "startAt": ["2"]},
    ]


@mock.patch("requests.Session.request")
def test_experimental(mock_request, mock_jira_client):
    out = mock_jira_client().mock_experimental_method("one", two="three")
    assert out is not None


@pytest.mark.parametrize("http_status_code", [404, 405])
@mock.patch("requests.Session.request")
def test_experimental_missing_or_not_allowed(
    mock_request, mock_jira_client, mock_response, http_status_code, caplog
):
    mock_response = mock_response(status_code=http_status_code)
    response = mock_jira_client().mock_method_raises_jira_error(
        response=mock_response,
        request=mock_response,
        status_code=mock_response.status_code,
    )
    assert response is None
    assert caplog.messages[0] == (
        f"Functionality at path {mock_response.url} is/was experimental. Status Code: "
        f"{mock_response.status_code}"
    )


@mock.patch("requests.Session.request")
def test_experimental_non_200_not_404_405(
    mock_request, mock_jira_client, mock_response
):
    status_code = 400
    mock_response = mock_response(status_code=status_code)

    with pytest.raises(JIRAError) as ex:
        mock_jira_client().mock_method_raises_jira_error(
            response=mock_response,
            request=mock_response,
            status_code=mock_response.status_code,
        )

    assert ex.value.status_code == status_code
    assert isinstance(ex.value, JIRAError)


def test_handle_401_preserves_send_kwargs():
    """Test that handle_401 passes kwargs to process_original_request"""

    auth = jira.client.JiraCookieAuth(
        session=mock.Mock(),
        session_api_url="https://mock",
        auth=("user", "pass"),
    )

    prepared_request = requests.Request(
        "GET",
        "https://mocked.jira.invalid/rest/api/2/myself",
    ).prepare()

    response_401 = mock.Mock()
    response_401.status_code = 401
    response_401.request = prepared_request
    response_401.text = "Unauthorized"

    retried_response = mock.Mock()
    retried_response.status_code = 200

    auth.process_original_request = mock.Mock(return_value=retried_response)
    auth.init_session = mock.Mock()

    kwargs = {
        "verify": "/usr/local/share/ca-certificates/root.crt",
        "stream": True,
        "cert": "/path/client.pem",
    }

    result = auth.handle_401(response_401, **kwargs)

    auth.process_original_request.assert_called_once_with(
        mock.ANY,
        **kwargs,
    )

    assert result == retried_response


def test_process_original_request_preserves_kwargs():
    """Test that process_original_request forwards kwargs to send_request"""
    auth = jira.client.JiraCookieAuth(
        session=mock.Mock(),
        session_api_url="https://mock",
        auth=("user", "pass"),
    )

    request = requests.Request(
        "GET",
        "https://mocked.jira.invalid/rest/api/2/myself",
    ).prepare()

    auth.update_cookies = mock.Mock()
    auth.send_request = mock.Mock(return_value=mock.Mock(status_code=200))

    kwargs = {
        "verify": "/usr/local/share/ca-certificates/root.crt",
        "stream": True,
        "cert": "/path/client.pem",
    }

    auth.process_original_request(request, **kwargs)

    auth.send_request.assert_called_once_with(
        request,
        **kwargs,
    )


def test_send_request_preserves_kwargs_to_session_send():
    """Test that send_request forwards kwargs to session.send"""
    session = mock.Mock()
    session.send.return_value = mock.Mock(status_code=200)

    auth = jira.client.JiraCookieAuth(
        session=session,
        session_api_url="https://mock",
        auth=("user", "pass"),
    )

    request = requests.Request(
        "GET",
        "https://mocked.jira.invalid/rest/api/2/myself",
    ).prepare()

    kwargs = {
        "verify": "/usr/local/share/ca-certificates/root.crt",
        "stream": True,
        "cert": "/path/client.pem",
    }

    auth.send_request(request, **kwargs)

    session.send.assert_called_once_with(request, **kwargs)


# --- Pagination when ``maxResults`` is larger than the server's page size ---
# Jira Cloud caps the number of items per request (100 for issue search), see
# https://github.com/pycontribs/jira/issues/1819


class _PagedServer:
    """Stand-in for ``JIRA._get_json`` that mimics a server capping page size."""

    def __init__(self, total: int, cap: int = 100, token_based: bool = False):
        self.total = total
        self.cap = cap
        self.token_based = token_based
        self.calls: list[dict] = []

    @staticmethod
    def _issue(i: int) -> dict:
        return {"id": str(i), "key": f"KEY-{i}", "self": f"http://example.com/{i}"}

    def __call__(self, path, params=None, base=None, use_post=False):
        params = dict(params or {})
        self.calls.append(params)
        if self.token_based:
            token = params.get("nextPageToken")
            start = int(token.split("-")[1]) if token else 0
        else:
            start = params.get("startAt", 0)
        size = min(params.get("maxResults", self.cap), self.cap)
        end = min(start + size, self.total)
        page: dict = {"issues": [self._issue(i) for i in range(start, end)]}
        if self.token_based:
            if end < self.total:
                page["nextPageToken"] = f"tok-{end}"
            else:
                page["isLast"] = True
        else:
            page.update({"startAt": start, "maxResults": size, "total": self.total})
        return page


@pytest.fixture()
def offline_jira(no_fields) -> jira.client.JIRA:
    return jira.client.JIRA(
        server="https://jira.atlassian.com", get_server_info=False, validate=False
    )


@pytest.mark.parametrize(
    "start_at, max_results, total, expected_calls",
    [
        (0, 50, 500, [{"maxResults": 50}]),
        (0, 100, 500, [{"maxResults": 100}]),
        (
            0,
            200,
            500,
            [{"maxResults": 200}, {"startAt": 100, "maxResults": 100}],
        ),
        (
            0,
            150,
            500,
            [{"maxResults": 150}, {"startAt": 100, "maxResults": 50}],
        ),
        (
            10,
            200,
            500,
            [{"startAt": 10, "maxResults": 200}, {"startAt": 110, "maxResults": 100}],
        ),
        (
            0,
            250,
            120,
            [{"maxResults": 250}, {"startAt": 100, "maxResults": 100}],
        ),
        (
            0,
            False,
            250,
            [
                {"maxResults": 100},
                {"startAt": 100, "maxResults": 100},
                {"startAt": 200, "maxResults": 100},
            ],
        ),
    ],
    ids=[
        "below cap: one request",
        "equal to cap: one request",
        "above cap: two full pages",
        "above cap: truncated to maxResults",
        "above cap: startAt offset is kept",
        "fewer available than requested",
        "maxResults=False fetches everything",
    ],
)
def test_fetch_pages_server_caps_page_size(
    offline_jira, start_at, max_results, total, expected_calls
):
    server = _PagedServer(total=total, cap=100)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(
            Issue, "issues", "search", start_at, max_results, {}
        )

    expected_len = min(max_results or total, total - start_at)
    assert [c for c in server.calls] == expected_calls
    assert len(issues) == expected_len
    assert [i.key for i in issues] == [
        f"KEY-{i}" for i in range(start_at, start_at + expected_len)
    ]
    assert issues.total == total


@pytest.mark.parametrize(
    "max_results, total, expected_calls, expected_next_token",
    [
        (50, 500, [{"maxResults": 50}], "tok-50"),
        (
            200,
            500,
            [{"maxResults": 200}, {"maxResults": 100, "nextPageToken": "tok-100"}],
            "tok-200",
        ),
        (
            150,
            500,
            [{"maxResults": 150}, {"maxResults": 50, "nextPageToken": "tok-100"}],
            "tok-150",
        ),
        (
            250,
            120,
            [{"maxResults": 250}, {"maxResults": 100, "nextPageToken": "tok-100"}],
            None,
        ),
        (
            False,
            250,
            [
                {"maxResults": 100},
                {"maxResults": 100, "nextPageToken": "tok-100"},
                {"maxResults": 100, "nextPageToken": "tok-200"},
            ],
            None,
        ),
    ],
    ids=[
        "below cap: one request",
        "above cap: two full pages",
        "above cap: truncated to maxResults",
        "fewer available than requested",
        "maxResults=False fetches everything",
    ],
)
def test_fetch_pages_search_token_server_caps_page_size(
    offline_jira, max_results, total, expected_calls, expected_next_token
):
    offline_jira.deploymentType = "Cloud"
    server = _PagedServer(total=total, cap=100, token_based=True)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages_searchToken(
            Issue, "issues", "search/jql", max_results, {}
        )

    expected_len = min(max_results or total, total)
    assert server.calls == expected_calls
    assert len(issues) == expected_len
    assert [i.key for i in issues] == [f"KEY-{i}" for i in range(expected_len)]
    assert issues.nextPageToken == expected_next_token


def test_fetch_pages_search_token_uses_default_batch_size(no_fields):
    """Regression test for https://github.com/pycontribs/jira/issues/2366."""
    client = jira.client.JIRA(
        server="https://jira.atlassian.com",
        get_server_info=False,
        validate=False,
        default_batch_sizes={Issue: 40},
    )
    client.deploymentType = "Cloud"
    server = _PagedServer(total=90, cap=100, token_based=True)
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages_searchToken(
            Issue, "issues", "search/jql", False, {}
        )

    assert server.calls == [
        {"maxResults": 40},
        {"maxResults": 40, "nextPageToken": "tok-40"},
        {"maxResults": 40, "nextPageToken": "tok-80"},
    ]
    assert len(issues) == 90


def test_fetch_pages_search_token_lets_backend_pick_batch_size(
    no_fields, requests_mock
):
    client = jira.client.JIRA(
        server="https://jira.atlassian.com",
        get_server_info=False,
        validate=False,
        default_batch_sizes={Resource: None},
    )
    client.deploymentType = "Cloud"
    requests_mock.post(
        "https://jira.atlassian.com/rest/api/2/search/jql",
        json={"issues": [_PagedServer._issue(0)], "isLast": True},
    )

    issues = client._fetch_pages_searchToken(
        Issue, "issues", "search/jql", False, {"jql": "project = KEY"}, use_post=True
    )

    assert requests_mock.last_request.json() == {"jql": "project = KEY"}
    assert len(issues) == 1


@pytest.mark.parametrize("is_cloud", [True, False], ids=["cloud", "server"])
def test_search_issues_max_results_above_server_cap(offline_jira, is_cloud):
    """Regression test for https://github.com/pycontribs/jira/issues/1819."""
    if is_cloud:
        offline_jira.deploymentType = "Cloud"
    server = _PagedServer(total=500, cap=100, token_based=is_cloud)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira.search_issues("project = KEY", maxResults=200)

    assert len(server.calls) == 2
    assert len(issues) == 200


@pytest.mark.parametrize("is_cloud", [True, False], ids=["cloud", "server"])
@pytest.mark.parametrize(
    "fields", [None, "*all", "*navigable,-comment"], ids=["default", "all", "mixed"]
)
def test_search_issues_skips_field_lookup_for_wildcards(
    requests_mock, is_cloud, fields
):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    if is_cloud:
        client.deploymentType = "Cloud"
    base = "https://jira.example.com/rest/api/2"
    requests_mock.get(f"{base}/field", json=[])
    requests_mock.get(f"{base}/search/jql", json={"issues": [], "isLast": True})
    requests_mock.get(f"{base}/search", json={"issues": [], "startAt": 0, "total": 0})

    client.search_issues("project = KEY", fields=fields)

    paths = [r.path for r in requests_mock.request_history]
    assert "/rest/api/2/field" not in paths
    assert len(paths) == 1


def test_search_issues_translates_named_fields(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    base = "https://jira.example.com/rest/api/2"
    requests_mock.get(
        f"{base}/field",
        json=[{"id": "customfield_10001", "clauseNames": ["Story Points"]}],
    )
    requests_mock.get(f"{base}/search", json={"issues": [], "startAt": 0, "total": 0})

    client.search_issues("project = KEY", fields="summary,Story Points")

    search = requests_mock.request_history[-1]
    assert search.qs["fields"] == ["summary", "customfield_10001"]


def test_fetch_pages_stops_on_is_last_for_full_final_page(offline_jira):
    def page(start: int, is_last: bool) -> dict:
        return {
            "startAt": start,
            "maxResults": 100,
            "isLast": is_last,
            "issues": [_PagedServer._issue(i) for i in range(start, start + 100)],
        }

    pages = iter([page(0, False), page(100, True)])
    with mock.patch.object(
        offline_jira, "_get_json", side_effect=lambda *a, **k: next(pages)
    ) as get_json:
        issues = offline_jira._fetch_pages(Issue, "issues", "search", 0, 300, {})

    assert get_json.call_count == 2
    assert len(issues) == 200
    assert issues.isLast is True


class _ScriptedServer:
    """Stand-in for ``JIRA._get_json`` that replays canned responses in order."""

    def __init__(self, *responses: Any):
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.requests: list[tuple[str, str, bool]] = []

    def __call__(self, path, params=None, base=JIRA.JIRA_BASE_URL, use_post=False):
        self.calls.append(copy.deepcopy(params))
        self.requests.append((path, base, use_post))
        return self.responses.pop(0)


def _offset_page(start: int, count: int, page_size: int = 100, **extra: Any) -> dict:
    return {
        "startAt": start,
        "maxResults": page_size,
        "issues": [_PagedServer._issue(i) for i in range(start, start + count)],
        **extra,
    }


def _keys(start: int, stop: int) -> list[str]:
    return [f"KEY-{i}" for i in range(start, stop)]


@pytest.mark.parametrize(
    "max_results, expected_calls",
    [
        (
            False,
            [
                {"jql": "x", "fields": ["a"], "maxResults": 100},
                {"jql": "x", "fields": ["a"], "startAt": 100, "maxResults": 100},
            ],
        ),
        (
            150,
            [
                {"jql": "x", "fields": ["a"], "maxResults": 150},
                {"jql": "x", "fields": ["a"], "startAt": 100, "maxResults": 50},
            ],
        ),
    ],
    ids=["fetch all", "up to maxResults"],
)
def test_fetch_pages_forwards_request_arguments(
    offline_jira, max_results, expected_calls
):
    server = _ScriptedServer(
        _offset_page(0, 100, total=150), _offset_page(100, 50, total=150)
    )
    params = {"jql": "x", "fields": ("a",)}
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(
            Issue,
            "issues",
            "board/1/issue",
            0,
            max_results,
            params,
            base=JIRA.AGILE_BASE_URL,
            use_post=True,
        )

    assert server.calls == expected_calls
    assert server.requests == [("board/1/issue", JIRA.AGILE_BASE_URL, True)] * 2
    assert params == {"jql": "x", "fields": ("a",)}
    assert [i.key for i in issues] == _keys(0, 150)
    assert (issues.startAt, issues.maxResults, issues.total, issues.isLast) == (
        0,
        100,
        150,
        False,
    )


@pytest.mark.parametrize(
    "max_results, expected_calls",
    [
        (
            False,
            [
                {"maxResults": 100},
                {"startAt": 100, "maxResults": 100},
                {"startAt": 200, "maxResults": 100},
            ],
        ),
        (
            250,
            [
                {"maxResults": 250},
                {"startAt": 100, "maxResults": 100},
                {"startAt": 200, "maxResults": 50},
            ],
        ),
    ],
    ids=["fetch all", "up to maxResults"],
)
def test_fetch_pages_without_total(offline_jira, max_results, expected_calls):
    server = _ScriptedServer(
        _offset_page(0, 100), _offset_page(100, 100), _offset_page(200, 30)
    )
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(
            Issue, "issues", "search", 0, max_results, {}
        )

    assert server.calls == expected_calls
    assert [i.key for i in issues] == _keys(0, 230)
    assert issues.total == 230
    assert issues.isLast is False


@pytest.mark.parametrize("max_results", [False, 50], ids=["fetch all", "up to 50"])
@pytest.mark.parametrize(
    "first_page, expected_total",
    [
        (_offset_page(0, 0, total=0), 0),
        (_offset_page(0, 0), 0),
        ({"issues": []}, 0),
    ],
    ids=["with total", "without total", "without paging keys"],
)
def test_fetch_pages_empty_first_page(
    offline_jira, max_results, first_page, expected_total
):
    server = _ScriptedServer(first_page)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(
            Issue, "issues", "search", 0, max_results, {}
        )

    assert len(server.calls) == 1
    assert list(issues) == []
    assert issues.total == expected_total
    assert issues.isLast is False


@pytest.mark.parametrize("max_results", [False, 300], ids=["fetch all", "up to 300"])
def test_fetch_pages_stops_on_empty_response(offline_jira, max_results):
    server = _ScriptedServer(_offset_page(0, 100), {})
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(
            Issue, "issues", "search", 0, max_results, {}
        )

    assert len(server.calls) == 2
    assert [i.key for i in issues] == _keys(0, 100)


@pytest.mark.parametrize("max_results", [False, 50], ids=["fetch all", "up to 50"])
def test_fetch_pages_list_response(offline_jira, max_results):
    server = _ScriptedServer([_PagedServer._issue(0), _PagedServer._issue(1)])
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(Issue, None, "list", 0, max_results)

    assert len(server.calls) == 1
    assert [i.key for i in issues] == _keys(0, 2)
    assert (issues.startAt, issues.maxResults, issues.total, issues.isLast) == (
        0,
        1,
        1,
        True,
    )


@pytest.mark.parametrize(
    "pages, expected_calls, expected_is_last",
    [
        ([_offset_page(0, 100, isLast=True)], 1, True),
        (
            [
                _offset_page(0, 100, isLast=False),
                _offset_page(100, 100, isLast=True),
            ],
            2,
            True,
        ),
    ],
    ids=["first page is last", "full later page is last"],
)
def test_fetch_pages_fetch_all_is_last(
    offline_jira, pages, expected_calls, expected_is_last
):
    server = _ScriptedServer(*pages)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert len(server.calls) == expected_calls
    assert len(issues) == sum(len(p["issues"]) for p in pages)
    assert issues.isLast is expected_is_last


def test_fetch_pages_fetch_all_without_max_results_in_response(offline_jira):
    def page(i: int, **extra: Any) -> dict:
        return {"issues": [_PagedServer._issue(i)], **extra}

    server = _ScriptedServer(page(0, total=3), page(1), page(2))
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert server.calls == [
        {"maxResults": 100},
        {"startAt": 1, "maxResults": 1},
        {"startAt": 2, "maxResults": 1},
    ]
    assert [i.key for i in issues] == _keys(0, 3)
    assert (issues.maxResults, issues.total) == (1, 3)


def test_fetch_pages_warns_when_server_caps_batch_size(offline_jira, caplog):
    offline_jira._options["default_batch_size"] = {Issue: 200}
    server = _PagedServer(total=150, cap=100)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        with caplog.at_level(logging.WARNING):
            issues = offline_jira._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert server.calls == [{"maxResults": 200}, {"startAt": 100, "maxResults": 100}]
    assert len(issues) == 150
    assert "'batch_size' set to 200, but only received 100 items" in caplog.text


class _FakeFuturesSession:
    """Records requests the way ``requests_futures.sessions.FuturesSession`` gets them."""

    instances: list[_FakeFuturesSession] = []

    def __init__(self, bodies: list[Any], session: Any, max_workers: Any):
        self.bodies = bodies
        self.session = session
        self.max_workers = max_workers
        self.requests: list[tuple[str, str, dict]] = []
        _FakeFuturesSession.instances.append(self)

    def _future(self) -> mock.Mock:
        response = requests.Response()
        response.status_code = 200
        body = self.bodies.pop(0)
        response._content = json.dumps(body).encode() if body is not None else b""
        return mock.Mock(result=mock.Mock(return_value=response))

    def get(self, url: str, **kwargs: Any) -> mock.Mock:
        self.requests.append(("get", url, copy.deepcopy(kwargs)))
        return self._future()

    def post(self, url: str, **kwargs: Any) -> mock.Mock:
        self.requests.append(("post", url, copy.deepcopy(kwargs)))
        return self._future()


@pytest.fixture()
def async_jira(offline_jira):
    """``offline_jira`` with the async option on and a fake ``requests_futures``."""
    future_bodies: list[Any] = []
    package = types.ModuleType("requests_futures")
    sessions = types.ModuleType("requests_futures.sessions")
    sessions.FuturesSession = functools.partial(_FakeFuturesSession, future_bodies)
    package.sessions = sessions
    offline_jira._options["async"] = True
    offline_jira._options["async_workers"] = 7
    _FakeFuturesSession.instances.clear()
    with mock.patch.dict(
        sys.modules,
        {"requests_futures": package, "requests_futures.sessions": sessions},
    ):
        yield offline_jira, future_bodies


@pytest.mark.parametrize("use_post", [False, True], ids=["get", "post"])
@pytest.mark.parametrize(
    "future_pages, expected_keys",
    [
        ([_offset_page(100, 100), _offset_page(200, 50)], _keys(0, 250)),
        ([None, _offset_page(200, 50)], _keys(0, 100) + _keys(200, 250)),
    ],
    ids=["all pages", "empty body is skipped"],
)
def test_fetch_pages_async_fetches_remaining_pages(
    async_jira, use_post, future_pages, expected_keys
):
    client, future_bodies = async_jira
    future_bodies.extend(future_pages)
    server = _ScriptedServer(_offset_page(0, 100, total=250))
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(
            Issue, "issues", "search", 0, False, {"jql": "x"}, use_post=use_post
        )

    assert server.calls == [{"jql": "x", "maxResults": 100}]
    (session,) = _FakeFuturesSession.instances
    assert session.session is client._session
    assert session.max_workers == 7
    url = client._get_url("search")
    expected = [{"jql": "x", "startAt": s, "maxResults": 100} for s in (100, 200)]
    if use_post:
        assert [(m, u, json.loads(k["data"])) for m, u, k in session.requests] == [
            ("post", url, p) for p in expected
        ]
    else:
        assert session.requests == [("get", url, {"params": p}) for p in expected]
    assert [i.key for i in issues] == expected_keys
    assert (issues.startAt, issues.maxResults, issues.total, issues.isLast) == (
        0,
        100,
        250,
        False,
    )


@pytest.mark.parametrize("use_post", [False, True], ids=["get", "post"])
def test_fetch_pages_async_uses_base(async_jira, use_post):
    client, future_bodies = async_jira
    future_bodies.extend([_offset_page(100, 100), _offset_page(200, 50)])
    server = _ScriptedServer(_offset_page(0, 100, total=250))
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(
            Issue,
            "issues",
            "board/1/issue",
            0,
            False,
            base=JIRA.AGILE_BASE_URL,
            use_post=use_post,
        )

    assert server.requests == [("board/1/issue", JIRA.AGILE_BASE_URL, use_post)]
    (session,) = _FakeFuturesSession.instances
    url = client._get_url("board/1/issue", base=JIRA.AGILE_BASE_URL)
    assert "/rest/agile/1.0/board/1/issue" in url
    assert [u for _, u, _ in session.requests] == [url, url]
    assert [i.key for i in issues] == _keys(0, 250)


@pytest.mark.parametrize(
    "first_page",
    [
        _offset_page(0, 100),
        _offset_page(0, 100, total=250, isLast=True),
        _offset_page(0, 100, total=100),
    ],
    ids=["without total", "isLast", "everything in first page"],
)
def test_fetch_pages_async_single_request(async_jira, first_page):
    client, _ = async_jira
    server = _ScriptedServer(first_page)
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert len(server.calls) == 1
    assert _FakeFuturesSession.instances == []
    assert [i.key for i in issues] == _keys(0, 100)


def test_fetch_pages_async_with_max_results_pages_synchronously(async_jira):
    client, _ = async_jira
    server = _PagedServer(total=500, cap=100)
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(Issue, "issues", "search", 0, 150, {})

    assert server.calls == [{"maxResults": 150}, {"startAt": 100, "maxResults": 50}]
    assert _FakeFuturesSession.instances == []
    assert [i.key for i in issues] == _keys(0, 150)


@pytest.mark.parametrize("max_results", [False, 150], ids=["fetch all", "up to 150"])
def test_fetch_pages_search_token_result_fields(offline_jira, max_results):
    offline_jira.deploymentType = "Cloud"
    server = _PagedServer(total=120, cap=100, token_based=True)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages_searchToken(
            Issue, "issues", "search/jql", max_results, {}
        )

    assert [i.key for i in issues] == _keys(0, 120)
    assert (issues.startAt, issues.maxResults, issues.total, issues.isLast) == (
        0,
        0,
        120,
        None,
    )
    assert issues.nextPageToken is None


@pytest.mark.parametrize("max_results", [False, 50], ids=["fetch all", "up to 50"])
@pytest.mark.parametrize(
    "first_page, expected_token",
    [({"issues": []}, None), ({"issues": [], "nextPageToken": "tok-0"}, "tok-0")],
    ids=["no token", "with token"],
)
def test_fetch_pages_search_token_empty_first_page(
    offline_jira, max_results, first_page, expected_token
):
    offline_jira.deploymentType = "Cloud"
    server = _ScriptedServer(first_page)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages_searchToken(
            Issue, "issues", "search/jql", max_results, {}
        )

    assert len(server.calls) == 1
    assert list(issues) == []
    assert issues.total == 0
    assert issues.nextPageToken == expected_token


def test_fetch_pages_search_token_forwards_request_arguments(offline_jira):
    offline_jira.deploymentType = "Cloud"
    server = _ScriptedServer(
        {
            "issues": [_PagedServer._issue(i) for i in range(100, 200)],
            "nextPageToken": "t2",
        },
        {"issues": [_PagedServer._issue(i) for i in range(200, 230)], "isLast": True},
    )
    params = {"jql": "x", "nextPageToken": "t1"}
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages_searchToken(
            Issue, "issues", "search/jql", False, params, use_post=True
        )

    assert server.calls == [
        {"jql": "x", "nextPageToken": "t1", "maxResults": 100},
        {"jql": "x", "nextPageToken": "t2", "maxResults": 100},
    ]
    assert server.requests == [("search/jql", JIRA.JIRA_BASE_URL, True)] * 2
    assert params == {"jql": "x", "nextPageToken": "t1"}
    assert [i.key for i in issues] == _keys(100, 230)
    assert issues.isLast is None


def test_project_securitylevels(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.get(
        "https://jira.example.com/rest/api/2/project/ABC/securitylevel",
        json={
            "levels": [
                {"id": "10000", "name": "Internal", "description": "Staff only"},
                {"id": "10001", "name": "Public", "description": "Everyone"},
            ]
        },
    )

    levels = client.project_securitylevels("ABC")

    assert [level.name for level in levels] == ["Internal", "Public"]
    assert all(isinstance(level, SecurityLevel) for level in levels)


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "http_method", "path", "response"),
    [
        ("project_roles", (10000,), {}, "GET", "project/10000/role", {}),
        ("project_components", (10000,), {}, "GET", "project/10000/components", []),
        ("project_versions", (10000,), {}, "GET", "project/10000/versions", []),
        ("project_avatars", (10000,), {}, "GET", "project/10000/avatars", {}),
        (
            "move_version",
            (10001,),
            {"position": "First"},
            "POST",
            "version/10001/move",
            {"id": "10001"},
        ),
        (
            "version_count_related_issues",
            (10001,),
            {},
            "GET",
            "version/10001/relatedIssueCounts",
            {"self": "x"},
        ),
        (
            "version_count_unresolved_issues",
            (10001,),
            {},
            "GET",
            "version/10001/unresolvedIssueCount",
            {"issuesUnresolvedCount": 0},
        ),
        ("delete_issue_link", (10002,), {}, "DELETE", "issueLink/10002", None),
    ],
)
def test_int_ids_build_url(
    requests_mock, method, args, kwargs, http_method, path, response
):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = f"https://jira.example.com/rest/api/2/{path}"
    requests_mock.register_uri(http_method, url, json=response)

    getattr(client, method)(*args, **kwargs)

    assert requests_mock.last_request.method == http_method
    assert requests_mock.last_request.url == url


def test_client_retry_config():
    client = jira.client.JIRA(
        server="https://jira.example.com",
        get_server_info=False,
        validate=False,
        max_retries=81,
        max_retry_delay=111,
    )

    assert client._session.max_retries == 81
    assert client._session.max_retry_delay == 111


def test_issue_remove_field_value_sends_remove_operation(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = "https://jira.example.com/rest/api/2/issue/10001"
    raw = {"id": "10001", "key": "ABC-1", "self": url, "fields": {}}
    requests_mock.put(url, status_code=204)
    requests_mock.get(url, json=raw)
    issue = Issue(client._options, client._session, raw=raw)

    issue.remove_field_value("labels", "old-label")

    put = next(r for r in requests_mock.request_history if r.method == "PUT")
    assert put.json() == {"update": {"labels": [{"remove": "old-label"}]}}


@pytest.mark.parametrize(
    "method, path", [("archive", "archive"), ("unarchive", "unarchive")]
)
def test_archive_issues_accepts_keys_and_issues(
    offline_jira, requests_mock, method, path
):
    offline_jira.deploymentType = "Cloud"
    url = f"https://jira.atlassian.com/rest/api/2/issue/{path}"
    response = {"numberOfIssuesUpdated": 2, "errors": {}}
    requests_mock.put(url, json=response)
    issue = Issue(
        offline_jira._options,
        offline_jira._session,
        raw={"id": "10002", "key": "ABC-2", "self": "x", "fields": {}},
    )

    result = getattr(offline_jira, f"{method}_issues")(iter(["ABC-1", issue, 10003]))

    assert result == response
    assert requests_mock.last_request.json() == {
        "issueIdsOrKeys": ["ABC-1", "ABC-2", "10003"]
    }


@pytest.mark.parametrize(
    "method, path", [("archive", "archive"), ("unarchive", "restore")]
)
def test_archive_issues_on_server_puts_each_issue(
    offline_jira, requests_mock, method, path
):
    offline_jira._version = (8, 20, 0)
    base = "https://jira.atlassian.com/rest/api/2/issue"
    for key in ("ABC-1", "ABC-2", "10003"):
        requests_mock.put(f"{base}/{key}/{path}", status_code=204)
    issue = Issue(
        offline_jira._options,
        offline_jira._session,
        raw={"id": "10002", "key": "ABC-2", "self": "x", "fields": {}},
    )

    result = getattr(offline_jira, f"{method}_issues")(iter(["ABC-1", issue, 10003]))

    assert [r.url for r in requests_mock.request_history] == [
        f"{base}/ABC-1/{path}",
        f"{base}/ABC-2/{path}",
        f"{base}/10003/{path}",
    ]
    assert result == {"numberOfIssuesUpdated": 3, "errors": {}}


@pytest.mark.parametrize(
    "status, message",
    [
        (401, "Unauthorized"),
        (403, "We couldn't archive an already archived issue."),
        (404, "Issue Does Not Exist"),
    ],
)
def test_archive_issues_on_server_raises_on_first_refusal(
    offline_jira, requests_mock, status, message
):
    offline_jira._version = (8, 20, 0)
    base = "https://jira.atlassian.com/rest/api/2/issue"
    requests_mock.put(f"{base}/ABC-1/archive", status_code=204)
    requests_mock.put(
        f"{base}/ABC-2/archive",
        status_code=status,
        json={"errorMessages": [message], "errors": {}},
    )
    requests_mock.put(f"{base}/ABC-3/archive", status_code=204)

    with pytest.raises(JIRAError) as raised:
        offline_jira.archive_issues(["ABC-1", "ABC-2", "ABC-3"])

    assert raised.value.status_code == status
    assert raised.value.url == f"{base}/ABC-2/archive"
    assert message in raised.value.text
    assert [r.url for r in requests_mock.request_history] == [
        f"{base}/ABC-1/archive",
        f"{base}/ABC-2/archive",
    ]


@pytest.mark.parametrize(
    "method, version, needed",
    [("archive", (7, 13, 0), "8.0"), ("unarchive", (8, 0, 0), "8.1")],
)
def test_archive_issues_on_old_server_raises_before_sending(
    offline_jira, requests_mock, method, version, needed
):
    offline_jira._version = version

    with pytest.raises(NotImplementedError, match=f"needs Jira {needed} or later"):
        getattr(offline_jira, f"{method}_issues")(["ABC-1"])
    assert requests_mock.call_count == 0


def test_comment_property_roundtrip(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = "https://jira.example.com/rest/api/2/comment/10500/properties"
    prop = {"key": "sd.public.comment", "value": {"internal": True}}
    requests_mock.put(f"{url}/sd.public.comment", status_code=204)
    requests_mock.get(f"{url}/sd.public.comment", json=prop)
    requests_mock.get(url, json={"keys": [{"key": "sd.public.comment"}]})

    client.add_comment_property("10500", "sd.public.comment", {"internal": True})
    single = client.comment_property("10500", "sd.public.comment")
    listed = client.comment_properties("10500")

    put = next(r for r in requests_mock.request_history if r.method == "PUT")
    assert put.json() == {"internal": True}
    assert isinstance(single, jira.resources.CommentProperty)
    assert single.value.internal is True
    assert single.self == f"{url}/sd.public.comment"
    assert [p.key for p in listed] == ["sd.public.comment"]


def test_worklogs_and_worklog_send_expand(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    base = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    worklog = {"id": "100", "self": f"{base}/100"}
    requests_mock.get(base, json={"worklogs": [worklog]})
    requests_mock.get(f"{base}/100", json=worklog)

    client.worklogs("ABC-1", expand="properties")
    client.worklog("ABC-1", "100", expand="properties")

    assert [r.qs for r in requests_mock.request_history] == [
        {"expand": ["properties"]},
        {"expand": ["properties"]},
    ]


@pytest.mark.parametrize("notify,expected", [(False, True), (True, False)])
def test_add_worklog_notify(requests_mock, notify, expected):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    url = "https://jira.example.com/rest/api/2/issue/ABC-1/worklog"
    requests_mock.post(url, json={"id": "100", "self": f"{url}/100"})

    client.add_worklog("ABC-1", timeSpent="1h", notify=notify)

    assert ("notifyUsers=false" in requests_mock.last_request.url) is expected


def test_add_attachment_accepts_bytes(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    content = b"example content"
    bodies: list[bytes] = []

    def respond(request, context):
        bodies.append(request.body.read())
        return [{"id": "10001", "filename": "example.txt", "size": len(content)}]

    requests_mock.post(
        "https://jira.example.com/rest/api/2/issue/QQ-1/attachments", json=respond
    )

    attachment = client.add_attachment("QQ-1", content, "example.txt")

    assert attachment.size == len(content)
    assert b'filename="example.txt"' in bodies[0]
    assert content in bodies[0]
    assert requests_mock.last_request.headers["X-Atlassian-Token"] == "no-check"


def test_add_attachment_stream_uses_its_name(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    bodies: list[bytes] = []

    def respond(request, context):
        bodies.append(request.body.read())
        return [{"id": "10001", "filename": "report.txt", "size": 7}]

    requests_mock.post(
        "https://jira.example.com/rest/api/2/issue/QQ-1/attachments", json=respond
    )
    stream = io.BytesIO(b"content")
    stream.name = "reports/report.txt"

    client.add_attachment("QQ-1", stream)

    assert b'filename="report.txt"' in bodies[0]


def test_add_attachment_stream_without_name_raises(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )

    with pytest.raises(ValueError, match="filename is required"):
        client.add_attachment("QQ-1", io.BytesIO(b"content"))

    assert not requests_mock.called


def test_add_attachment_bytes_without_filename_raises(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )

    with pytest.raises(ValueError, match="filename is required"):
        client.add_attachment("QQ-1", b"example content")

    assert not requests_mock.called


@pytest.mark.parametrize(
    "buff, expected",
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png"),
        (b"GIF87a\x01\x00\x01\x00", "image/gif"),
        (b"GIF89a\x01\x00\x01\x00", "image/gif"),
        (b"BM\x3a\x00\x00\x00", "image/bmp"),
        (b"RIFF\x24\x00\x00\x00WEBP" + b"VP8 ", None),
        # 9x2 pixels: 2 bytes per row, 2 rows
        (b"\x00\x00\x09\x02" + b"\xff\x80" * 2, "image/vnd.wap.wbmp"),
        # 200x1 pixels: width as the multi-byte integer 0x81 0x48
        (b"\x00\x00\x81\x48\x01" + b"\x00" * 25, "image/vnd.wap.wbmp"),
        (b"\x00\x00\x09\x02\xff", None),
        (b"\x00\x00\x00\x00", None),
        (b"%PDF-1.7", None),
        (b"", None),
    ],
    ids=[
        "jpeg",
        "png",
        "gif87a",
        "gif89a",
        "bmp",
        "webp is not documented",
        "wbmp",
        "wbmp multi-byte width",
        "zero-led bytes too short for wbmp",
        "wbmp with zero size",
        "unsupported",
        "empty",
    ],
)
def test_get_mime_type(buff, expected):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    if expected is None:
        with pytest.raises(ValueError, match="contentType"):
            client._get_mime_type(buff)
    else:
        assert client._get_mime_type(buff) == expected


def test_fetch_pages_uses_caller_start_at_when_response_has_none(offline_jira):
    def page(start: int) -> dict:
        return {
            "maxResults": 100,
            "total": 250,
            "issues": [_PagedServer._issue(i) for i in range(start, start + 100)],
        }

    server = _ScriptedServer(page(50), page(150))
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        offline_jira._fetch_pages(Issue, "issues", "search", 50, False, {})

    assert server.calls[1]["startAt"] == 150


def test_fetch_pages_up_to_stops_when_start_reaches_total(offline_jira):
    server = _PagedServer(total=200, cap=100)
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages(Issue, "issues", "search", 0, 300, {})

    assert server.calls == [{"maxResults": 300}, {"startAt": 100, "maxResults": 100}]
    assert len(issues) == 200


def test_fetch_pages_search_token_truncates_to_max_results(offline_jira):
    offline_jira.deploymentType = "Cloud"
    server = _ScriptedServer(
        {
            "issues": [_PagedServer._issue(i) for i in range(100)],
            "nextPageToken": "t1",
        }
    )
    with mock.patch.object(offline_jira, "_get_json", side_effect=server):
        issues = offline_jira._fetch_pages_searchToken(
            Issue, "issues", "search/jql", 50, {}
        )

    assert len(server.calls) == 1
    assert [i.key for i in issues] == _keys(0, 50)


def _link_type(client, name, inward, outward, id):
    raw = {"id": id, "name": name, "inward": inward, "outward": outward}
    return IssueLinkType(client._options, client._session, raw=raw)


@pytest.fixture()
def link_client(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.post("https://jira.example.com/rest/api/2/issueLink", status_code=201)
    link_types = [
        _link_type(client, "Problem/Incident", "Duplicate", "causes", "1"),
        _link_type(client, "Duplicate", "is duplicated by", "duplicates", "2"),
    ]
    with mock.patch.object(client, "issue_link_types", return_value=link_types):
        yield client, link_types


@pytest.mark.parametrize(
    "type_arg,expected_id,inward,outward",
    [
        ("Duplicate", "2", "A-1", "B-1"),
        ("duplicates", "2", "A-1", "B-1"),
        ("is duplicated by", "2", "B-1", "A-1"),
        ("causes", "1", "A-1", "B-1"),
    ],
)
def test_create_issue_link_resolves_type(
    link_client, requests_mock, type_arg, expected_id, inward, outward
):
    client, _ = link_client

    client.create_issue_link(type_arg, "A-1", "B-1")

    body = requests_mock.last_request.json()
    assert body["type"]["id"] == expected_id
    assert body["inwardIssue"] == {"key": inward}
    assert body["outwardIssue"] == {"key": outward}


@pytest.mark.parametrize("as_keyword", [False, True])
def test_create_issue_link_accepts_issue_link_type(
    link_client, requests_mock, caplog, as_keyword
):
    client, link_types = link_client

    if as_keyword:
        client.create_issue_link(
            type=link_types[1], inwardIssue="A-1", outwardIssue="B-1"
        )
    else:
        client.create_issue_link(link_types[1], "A-1", "B-1")

    body = requests_mock.last_request.json()
    assert body["type"]["name"] == "Duplicate"
    assert body["inwardIssue"] == {"key": "A-1"}
    assert "not present" not in caplog.text


def test_create_issue_link_warns_on_unknown_type(link_client, requests_mock, caplog):
    client, _ = link_client

    with caplog.at_level(logging.WARNING):
        client.create_issue_link("Clones", "A-1", "B-1")

    assert requests_mock.last_request.json()["type"] == {"name": "Clones"}
    assert "Clones" in caplog.text


def test_resources_passed_by_keyword_send_their_key(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    base = "https://jira.example.com/rest/api/2"
    inward = Issue(client._options, client._session, raw={"id": "1", "key": "ABC-1"})
    outward = Issue(client._options, client._session, raw={"id": "2", "key": "ABC-2"})
    requests_mock.get(f"{base}/issue/ABC-1/comment/5", json={"id": "5"})
    requests_mock.get(
        f"{base}/issueLinkType",
        json={
            "issueLinkTypes": [
                {
                    "id": "1",
                    "name": "Blocks",
                    "inward": "is blocked by",
                    "outward": "blocks",
                }
            ]
        },
    )
    requests_mock.post(f"{base}/issueLink", status_code=201)

    client.comment(issue=inward, comment=5)
    client.create_issue_link(type="Blocks", inwardIssue=inward, outwardIssue=outward)

    assert requests_mock.request_history[0].url == f"{base}/issue/ABC-1/comment/5"
    assert requests_mock.last_request.json() == {
        "type": {
            "id": "1",
            "name": "Blocks",
            "inward": "is blocked by",
            "outward": "blocks",
        },
        "inwardIssue": {"key": "ABC-1"},
        "outwardIssue": {"key": "ABC-2"},
        "comment": None,
    }


def test_translate_resource_args_passes_resource_when_annotation_accepts_it():
    issue = Issue({}, mock.Mock(), raw={"id": "1", "key": "ABC-1"})

    @jira.client.translate_resource_args
    def accepts_issue(x: Issue | str) -> Any:
        return x

    @jira.client.translate_resource_args
    def accepts_any_resource(x: Resource | None = None) -> Any:
        return x

    @jira.client.translate_resource_args
    def wants_str(x: str) -> Any:
        return x

    @jira.client.translate_resource_args
    def takes_fields(**fields: Any) -> Any:
        return fields["x"]

    assert accepts_issue(issue) is issue
    assert accepts_issue(x=issue) is issue
    assert accepts_any_resource(issue) is issue
    assert wants_str(issue) == "ABC-1"
    assert wants_str(x=issue) == "ABC-1"
    assert takes_fields(x=issue) is issue


def test_translate_resource_args_converts_when_hints_do_not_resolve():
    issue = Issue({}, mock.Mock(), raw={"id": "1", "key": "ABC-1"})

    @jira.client.translate_resource_args
    def unresolvable(x: Issue | NotDefinedAnywhere) -> Any:  # type: ignore[name-defined] # noqa: F821
        return x

    assert unresolvable(issue) == "ABC-1"


SPRINT_REPORT_URL = (
    "https://jira.example.com/rest/greenhopper/1.0/rapid/charts/sprintreport"
    "?rapidViewId=1&sprintId=2"
)
SPRINT_REPORT = {
    "contents": {
        "completedIssues": [{"id": "10", "key": "ABC-10"}],
        "puntedIssues": [{"id": "20", "key": "ABC-20"}],
        "issuesNotCompletedEstimateSum": {"value": 3.0, "text": "3.0"},
        "puntedIssuesEstimateSum": {"value": 5.0, "text": "5.0"},
    }
}


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("incompletedIssuesEstimateSum", 3.0),
        ("removedIssuesEstimateSum", 5.0),
        ("removed_issues", ["ABC-20"]),
    ],
)
def test_sprint_report_methods_use_greenhopper_api(requests_mock, method, expected):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.get(SPRINT_REPORT_URL, json=SPRINT_REPORT)

    result = getattr(client, method)("1", "2")

    if isinstance(result, list):
        result = [issue.key for issue in result]
    assert result == expected


def test_completed_issues_reads_sprint_report(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.get(SPRINT_REPORT_URL, json=SPRINT_REPORT)

    issues = client.completed_issues("1", "2")

    assert [issue.key for issue in issues] == ["ABC-10"]
    assert all(isinstance(issue, Issue) for issue in issues)


@pytest.mark.parametrize(
    "method", ["incompletedIssuesEstimateSum", "removedIssuesEstimateSum"]
)
def test_sprint_report_estimate_sum_is_none_without_estimates(requests_mock, method):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    no_estimate = {"text": "null"}
    requests_mock.get(
        SPRINT_REPORT_URL,
        json={
            "contents": {
                "issuesNotCompletedEstimateSum": no_estimate,
                "puntedIssuesEstimateSum": no_estimate,
            }
        },
    )

    assert getattr(client, method)("1", "2") is None


def test_find_transitionid_by_name_returns_string_id(requests_mock):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    requests_mock.get(
        "https://jira.example.com/rest/api/2/issue/ABC-1/transitions",
        json={"transitions": [{"id": "11", "name": "To Do"}]},
    )

    assert client.find_transitionid_by_name("ABC-1", "to do") == "11"


@pytest.mark.parametrize(
    "name", ["comments", "enhanced_search_issues", "create_dashboard"]
)
def test_decorated_methods_keep_name_and_docstring(name):
    method = getattr(jira.client.JIRA, name)
    assert method.__name__ == name
    assert method.__doc__
    assert method.__doc__ == inspect.unwrap(method).__doc__


def test_create_version_returns_without_sleeping(requests_mock, monkeypatch):
    client = jira.client.JIRA(
        server="https://jira.example.com", get_server_info=False, validate=False
    )
    monkeypatch.setattr(
        jira.client.time, "sleep", mock.Mock(side_effect=AssertionError)
    )
    requests_mock.post(
        "https://jira.example.com/rest/api/2/version",
        json={"id": "10000", "name": "1.0", "projectId": 10000},
    )

    version = client.create_version("1.0", "PROJ")

    assert isinstance(version, Version)
    assert version.id == "10000"
    assert requests_mock.last_request.json()["project"] == "PROJ"
