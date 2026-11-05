from __future__ import annotations

import copy
import functools
import inspect
import json
import logging
import sys
import types
from typing import Any
from unittest import mock

import pytest
import requests
import requests.sessions

import jira.client
from jira.client import JIRA
from jira.exceptions import JIRAError, NotJIRAInstanceError
from jira.resources import (
    Issue,
    Resource,
)
from tests.conftest import allow_on_cloud

pytestmark = pytest.mark.unit


@pytest.fixture()
def prep():
    pass


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
def mock_response():
    class MockResponse:
        def __init__(self, status_code=404):
            self.status_code = status_code
            self.url = "some/url/that/does/not/exist"

    return MockResponse


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
        _offset_page(0, 100, total=250, isLast=True),
        _offset_page(0, 100, total=100),
    ],
    ids=["isLast", "everything in first page"],
)
def test_fetch_pages_async_single_request(async_jira, first_page):
    client, _ = async_jira
    server = _ScriptedServer(first_page)
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert len(server.calls) == 1
    assert _FakeFuturesSession.instances == []
    assert [i.key for i in issues] == _keys(0, 100)


def test_fetch_pages_async_without_total_pages_synchronously_until_is_last(
    async_jira,
):
    client, _ = async_jira
    server = _ScriptedServer(
        _offset_page(0, 100, isLast=False),
        _offset_page(100, 100, isLast=False),
        _offset_page(200, 50, isLast=True),
    )
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(Issue, "issues", "search", 0, False, {})

    assert server.calls == [
        {"maxResults": 100},
        {"startAt": 100, "maxResults": 100},
        {"startAt": 200, "maxResults": 100},
    ]
    assert _FakeFuturesSession.instances == []
    assert [i.key for i in issues] == _keys(0, 250)
    assert issues.isLast is True


def test_fetch_pages_async_with_max_results_pages_synchronously(async_jira):
    client, _ = async_jira
    server = _PagedServer(total=500, cap=100)
    with mock.patch.object(client, "_get_json", side_effect=server):
        issues = client._fetch_pages(Issue, "issues", "search", 0, 150, {})

    assert server.calls == [{"maxResults": 150}, {"startAt": 100, "maxResults": 50}]
    assert _FakeFuturesSession.instances == []
    assert [i.key for i in issues] == _keys(0, 150)


def test_async_without_requests_futures_warns_and_fetches_all_pages(requests_mock):
    url = "https://jira.example.com/rest/api/2/dashboard"

    def page(start: int) -> dict:
        ids = range(start, min(start + 2, 5))
        return {
            "startAt": start,
            "maxResults": 2,
            "total": 5,
            "dashboards": [{"id": str(i), "self": f"{url}/{i}"} for i in ids],
        }

    requests_mock.get(url, [{"json": page(0)}, {"json": page(2)}, {"json": page(4)}])

    options = {"async": True}

    with mock.patch.object(JIRA, "_futures_session_class", return_value=None):
        with pytest.warns(UserWarning, match="requests-futures"):
            client = jira.client.JIRA(
                server="https://jira.example.com",
                options=options,
                get_server_info=False,
                validate=False,
            )
        dashboards = client.dashboards(maxResults=False)

    assert client._options["async"] is False
    assert options["async"] is True
    assert [d.id for d in dashboards] == ["0", "1", "2", "3", "4"]


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


@pytest.mark.parametrize(
    "name", ["comments", "enhanced_search_issues", "create_dashboard"]
)
def test_decorated_methods_keep_name_and_docstring(name):
    method = getattr(jira.client.JIRA, name)
    assert method.__name__ == name
    assert method.__doc__
    assert method.__doc__ == inspect.unwrap(method).__doc__
