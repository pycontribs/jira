from __future__ import annotations

import json
import threading
import warnings
from unittest import mock

import pytest
import requests
import requests_mock as rm
from requests_toolbelt import MultipartEncoder

import jira.client
from jira.client import JiraCookieAuth, TokenAuth
from jira.exceptions import JIRAError
from jira.resilientsession import ResilientSession
from tests.conftest import JiraTestManager

SERVER = "https://mocked.jira.invalid"
MYSELF = f"{SERVER}/rest/api/2/myself"
SESSION_API = f"{SERVER}/rest/auth/1/session"


def _cookie_session() -> ResilientSession:
    session = ResilientSession()
    session.auth = JiraCookieAuth(session, SESSION_API, ("user", "pass"))
    return session


def _token_session() -> ResilientSession:
    session = ResilientSession()
    session.auth = TokenAuth("tok", session=session)
    return session


AUTH_SESSIONS = [_cookie_session, _token_session]


def _reject_session_cookie(request, context):
    if "JSESSIONID" in request.headers.get("Cookie", ""):
        context.status_code = 401
        return {}
    return {"name": "user"}


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


@pytest.mark.unit
class TestAuthOffline:
    def test_cookie_auth_retry(self, requests_mock):
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

    def test_cookie_auth_retries_401_with_fresh_session_cookie(self, requests_mock):
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
        assert json.loads(login_request.text) == {
            "username": "user",
            "password": "pass",
        }
        assert retry.headers["Cookie"] == "JSESSIONID=fresh"

    @pytest.mark.parametrize("make_session", AUTH_SESSIONS)
    def test_auth_ok_response_sends_once(self, requests_mock, make_session):
        session = make_session()
        session.cookies.set("JSESSIONID", "current")
        requests_mock.get(MYSELF, json={})

        session.get(MYSELF)

        assert len(requests_mock.request_history) == 1
        assert session.cookies.get("JSESSIONID") == "current"

    @pytest.mark.parametrize("make_session", AUTH_SESSIONS)
    def test_auth_retries_401_once(self, requests_mock, make_session):
        session = make_session()
        session.cookies.set("JSESSIONID", "stale")
        requests_mock.post(SESSION_API, json={})
        requests_mock.get(MYSELF, status_code=401)

        with pytest.raises(JIRAError):
            session.get(MYSELF)

        assert sum(r.url == MYSELF for r in requests_mock.request_history) == 2

    @pytest.mark.parametrize("make_session", AUTH_SESSIONS)
    def test_auth_does_not_retry_streamed_body(self, requests_mock, make_session):
        session = make_session()
        session.cookies.set("JSESSIONID", "stale")
        requests_mock.post(SESSION_API, json={})
        requests_mock.post(MYSELF, status_code=401)
        upload = MultipartEncoder(fields={"file": ("a.txt", b"data")})

        with pytest.raises(JIRAError):
            session.post(
                MYSELF, data=upload, headers={"Content-Type": upload.content_type}
            )

        assert [r.url for r in requests_mock.request_history] == [MYSELF]

    @pytest.mark.parametrize("make_session", AUTH_SESSIONS)
    @pytest.mark.parametrize("recovers", [True, False], ids=["recovers", "persistent"])
    def test_auth_retries_401_once_per_async_request(self, make_session, recovers):
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
    def test_auth_retry_keeps_send_kwargs(self, requests_mock, make_session):
        session = make_session()
        session.cookies.set("JSESSIONID", "stale")
        requests_mock.post(SESSION_API, json={})
        requests_mock.get(MYSELF, [{"status_code": 401}, {"json": {}}])
        send_kwargs = {"verify": "/ca.pem", "cert": "/client.pem", "stream": True}

        with mock.patch.object(session, "send", wraps=session.send) as send:
            response = session.get(MYSELF, **send_kwargs)

        assert response.status_code == 200
        retry_call = send.call_args_list[-1]
        assert retry_call.args[0].url == MYSELF
        assert retry_call.kwargs.items() >= send_kwargs.items()

    def test_token_auth_retries_401_without_cookies(self, requests_mock):
        session = _token_session()
        session.cookies.set("JSESSIONID", "stale")
        session.cookies.set("persistent", "kept", expires=4102444800, discard=False)
        requests_mock.get(MYSELF, json=_reject_session_cookie)

        response = session.get(MYSELF)

        assert response.status_code == 200
        first, retry = requests_mock.request_history
        assert "JSESSIONID=stale" in first.headers["Cookie"]
        assert "Cookie" not in retry.headers
        assert retry.headers["Authorization"] == "Bearer tok"
        assert "JSESSIONID" not in session.cookies
        assert session.cookies.get("persistent") == "kept"

    def test_token_auth_does_not_retry_401_without_cookie(self, requests_mock):
        session = _token_session()
        requests_mock.get(MYSELF, status_code=401)

        with pytest.raises(JIRAError):
            session.get(MYSELF)

        assert len(requests_mock.request_history) == 1

    def test_token_auth_without_session_sends_bearer(self, requests_mock):
        session = requests.Session()
        session.auth = TokenAuth("tok")
        requests_mock.get(MYSELF, json={})

        session.get(MYSELF)

        assert requests_mock.last_request.headers["Authorization"] == "Bearer tok"

    def test_token_auth_without_session_warns_on_401_with_cookie(self, requests_mock):
        session = requests.Session()
        session.auth = TokenAuth("tok")
        session.cookies.set("JSESSIONID", "stale")
        requests_mock.get(MYSELF, status_code=401)

        with pytest.warns(UserWarning, match="JRASERVER-76340"):
            response = session.get(MYSELF)

        assert response.status_code == 401
        assert len(requests_mock.request_history) == 1

    def test_token_auth_without_session_silent_on_401_without_cookie(
        self,
        requests_mock,
    ):
        session = requests.Session()
        session.auth = TokenAuth("tok")
        requests_mock.get(MYSELF, status_code=401)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            response = session.get(MYSELF)

        assert response.status_code == 401

    def test_bearer_token_auth(self):
        my_token = "cool-token"
        token_auth_jira = jira.client.JIRA(
            server="https://what.ever",
            token_auth=my_token,
            get_server_info=False,
            validate=False,
        )
        method_send = token_auth_jira._session.send
        with mock.patch.object(
            token_auth_jira._session, method_send.__name__
        ) as mock_send:
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
