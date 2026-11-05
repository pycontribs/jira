from __future__ import annotations

from unittest import mock

import pytest
import requests_mock as rm

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


def test_unit_cookie_auth_retry(requests_mock):
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


@pytest.mark.parametrize("make_session", [_cookie_session])
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
