from __future__ import annotations

import json
import threading
from unittest import mock

import pytest
import requests
import requests_mock as rm
from requests_toolbelt import MultipartEncoder

import jira.client
from jira.client import JiraCookieAuth
from jira.exceptions import JIRAError
from jira.resilientsession import ResilientSession

SERVER = "https://mocked.jira.invalid"
MYSELF = f"{SERVER}/rest/api/2/myself"
SESSION_API = f"{SERVER}/rest/auth/1/session"


def _cookie_session() -> ResilientSession:
    session = ResilientSession()
    session.auth = JiraCookieAuth(session, SESSION_API, ("user", "pass"))
    return session


AUTH_SESSIONS = [_cookie_session]


def test_unit_cookie_auth_retry(requests_mock):
    """Test Cookie based authentication retry logic works."""
    # GIVEN: a mocked Jira that always returns 401 on the auth URL
    new_options = jira.client.JIRA.DEFAULT_OPTIONS.copy()
    new_options["auth_url"] = "/401"
    requests_mock.register_uri(
        rm.ANY,
        "https://mocked.jira.invalid/401",
        status_code=401,
    )
    with pytest.raises(JIRAError):
        # WHEN: We create a session with cookie auth
        jira.client.JIRA(
            server="https://mocked.jira.invalid",
            options=new_options,
            auth=("user", "pass"),
        )
    # THEN: the failed request is followed by one login attempt, no recursion
    assert [r.method for r in requests_mock.request_history] == ["GET", "POST"]


def test_unit_cookie_auth_retries_401_with_fresh_session_cookie(requests_mock):
    session = _cookie_session()
    session.cookies.set("JSESSIONID", "stale")

    def login(request, context):
        # requests_mock does not feed Set-Cookie into the session's cookie jar
        session.cookies.set("JSESSIONID", "fresh")
        return {}

    requests_mock.post(SESSION_API, json=login)
    requests_mock.get(MYSELF, [{"status_code": 401}, {"json": {"name": "user"}}])

    response = session.get(MYSELF)

    assert response.status_code == 200
    first, login_request, retry = requests_mock.request_history
    assert first.headers["Cookie"] == "JSESSIONID=stale"
    assert json.loads(login_request.text) == {"username": "user", "password": "pass"}
    assert retry.headers["Cookie"] == "JSESSIONID=fresh"


@pytest.mark.parametrize("make_session", AUTH_SESSIONS)
def test_unit_auth_ok_response_sends_once(requests_mock, make_session):
    session = make_session()
    session.cookies.set("JSESSIONID", "current")
    requests_mock.get(MYSELF, json={})

    session.get(MYSELF)

    assert len(requests_mock.request_history) == 1
    assert session.cookies.get("JSESSIONID") == "current"


@pytest.mark.parametrize("make_session", AUTH_SESSIONS)
def test_unit_auth_retries_401_once(requests_mock, make_session):
    session = make_session()
    session.cookies.set("JSESSIONID", "stale")
    requests_mock.post(SESSION_API, json={})
    requests_mock.get(MYSELF, status_code=401)

    with pytest.raises(JIRAError):
        session.get(MYSELF)

    assert sum(r.url == MYSELF for r in requests_mock.request_history) == 2


@pytest.mark.parametrize("make_session", AUTH_SESSIONS)
def test_unit_auth_does_not_retry_streamed_body(requests_mock, make_session):
    session = make_session()
    session.cookies.set("JSESSIONID", "stale")
    requests_mock.post(SESSION_API, json={})
    requests_mock.post(MYSELF, status_code=401)
    upload = MultipartEncoder(fields={"file": ("a.txt", b"data")})

    with pytest.raises(JIRAError):
        session.post(MYSELF, data=upload, headers={"Content-Type": upload.content_type})

    assert [r.url for r in requests_mock.request_history] == [MYSELF]


class _ThreadedServer(requests.adapters.BaseAdapter):
    """Answers on the sending thread; requests_mock locks around every send."""

    def __init__(self, status_for):
        super().__init__()
        self.status_for = status_for
        self.urls: list[str] = []

    def send(self, request, **kwargs):
        self.urls.append(request.url)
        response = requests.Response()
        response.status_code = self.status_for(request)
        response.request = request
        response.url = request.url
        response._content = b"{}"
        return response

    def close(self):
        pass


@pytest.mark.parametrize("make_session", AUTH_SESSIONS)
@pytest.mark.parametrize("recovers", [True, False], ids=["recovers", "persistent"])
def test_unit_auth_retries_401_once_per_async_request(make_session, recovers):
    futures_sessions = pytest.importorskip("requests_futures.sessions")
    workers = 4
    session = make_session()
    session.cookies.set("JSESSIONID", "stale")
    # Every request reaches its 401, and every re-login is under way, before any
    # proceeds, so all workers are retrying at the same time.
    first_401s = threading.Barrier(workers, timeout=10)
    logins = threading.Barrier(workers, timeout=10)

    def status_for(request):
        if request.url == SESSION_API:
            logins.wait()
            session.cookies.set("JSESSIONID", "fresh")
            return 200
        if "JSESSIONID=stale" in request.headers.get("Cookie", ""):
            first_401s.wait()
            return 401
        return 200 if recovers else 401

    server = _ThreadedServer(status_for)
    session.mount(SERVER, server)
    async_session = futures_sessions.FuturesSession(
        session=session, max_workers=workers
    )
    futures = [async_session.get(MYSELF) for _ in range(workers)]

    for future in futures:
        if recovers:
            assert future.result().status_code == 200
        else:
            with pytest.raises(JIRAError):
                future.result()
    assert server.urls.count(MYSELF) == 2 * workers


@pytest.mark.parametrize("make_session", AUTH_SESSIONS)
def test_unit_auth_retry_keeps_send_kwargs(requests_mock, make_session):
    session = make_session()
    requests_mock.post(SESSION_API, json={})
    requests_mock.get(MYSELF, [{"status_code": 401}, {"json": {}}])
    send_kwargs = {"verify": "/ca.pem", "cert": "/client.pem", "stream": True}

    with mock.patch.object(session, "send", wraps=session.send) as send:
        response = session.get(MYSELF, **send_kwargs)

    assert response.status_code == 200
    retry_call = send.call_args_list[-1]
    assert retry_call.args[0].url == MYSELF
    assert retry_call.kwargs.items() >= send_kwargs.items()
