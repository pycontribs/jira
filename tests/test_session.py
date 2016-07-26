import pytest
import requests
from jira import JIRAError, JIRA


def test_session(jira_admin):
    user = jira_admin.session()

    assert user.raw['session'] is not None


def test_session_with_no_logged_in_user_raises():
    anon_jira = JIRA('https://support.atlassian.com', logging=False)
    with pytest.raises(JIRAError):
        anon_jira.session()


def test_session_server_offline():
    try:
        JIRA('https://127.0.0.1:1', logging=False, max_retries=0)
    except Exception as e:
        assert type(e) in (
            JIRAError,
            requests.exceptions.ConnectionError,
            AttributeError
        )
        return

    assert False, "Instantiation of invalid JIRA instance succeeded."
