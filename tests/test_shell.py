# -*- coding: utf-8 -*-
import io
import sys
from unittest.mock import MagicMock, patch

import pytest  # noqa
import requests  # noqa

import jira.jirashell as jirashell
from jira import JIRA, Issue, JIRAError, Project, Role  # noqa


@pytest.fixture
def testargs():
    return ["jirashell", "-s", "http://localhost"]


def test_unicode(requests_mock, capsys, testargs):
    """This functions tests that CLI tool does not throw an UnicodeDecodeError
    when it attempts to display some Unicode error message, which can happen
    when printing exceptions received from the remote HTTP server.
    """
    requests_mock.register_uri(
        "GET",
        "http://localhost/rest/api/2/serverInfo",
        text="Δεν βρέθηκε",
        status_code=404,
    )

    with patch.object(sys, "argv", testargs):
        jirashell.main()
    captured = capsys.readouterr()
    assert captured.err.startswith("JiraError HTTP 404")
    assert captured.out == ""


@pytest.fixture
def mock_keyring():
    _keyring = {}

    def mock_set_password(server, username, password):
        _keyring[(server, username)] = password

    def mock_get_password(server, username):
        return _keyring.get((server, username), "")

    mock_kr = MagicMock(
        set_password=MagicMock(side_effect=mock_set_password),
        get_password=MagicMock(side_effect=mock_get_password),
        _keyring=_keyring,
    )
    mocked_module = patch.object(jirashell, "keyring", new=mock_kr)
    yield mocked_module.start()
    mocked_module.stop()


@pytest.mark.timeout(4)
def test_no_password_try_keyring(
    requests_mock, capsys, testargs, mock_keyring, monkeypatch
):
    requests_mock.register_uri(
        "GET", "http://localhost/rest/api/2/serverInfo", status_code=200
    )

    # no password provided
    args = testargs + ["-u", "test@user"]
    with patch.object(sys, "argv", args):
        jirashell.main()

        assert len(requests_mock.request_history) == 0
        captured = capsys.readouterr()
        assert captured.err == "No password provided!\nassert ''\n"
        assert "Getting password from keyring..." == captured.out.strip()
        assert mock_keyring._keyring == {}

    # password provided, don't save
    monkeypatch.setattr("sys.stdin", io.StringIO("n"))
    args = args + ["-p", "pass123"]
    with patch.object(sys, "argv", args):
        jirashell.main()

        assert len(requests_mock.request_history) == 4
        captured = capsys.readouterr()
        assert captured.out.strip().startswith(
            "Would you like to remember password in OS keyring? (y/n)"
        )
        assert mock_keyring._keyring == {}

    # password provided, save
    monkeypatch.setattr("sys.stdin", io.StringIO("y"))
    args = args + ["-p", "pass123"]
    with patch.object(sys, "argv", args):
        jirashell.main()

        assert len(requests_mock.request_history) == 8
        captured = capsys.readouterr()
        assert captured.out.strip().startswith(
            "Would you like to remember password in OS keyring? (y/n)"
        )
        assert mock_keyring._keyring == {("http://localhost", "test@user"): "pass123"}

    # user stored password
    args = testargs + ["-u", "test@user"]
    with patch.object(sys, "argv", args):
        jirashell.main()

        assert len(requests_mock.request_history) == 12
        captured = capsys.readouterr()
        assert "Getting password from keyring..." == captured.out.strip()
        assert mock_keyring._keyring == {("http://localhost", "test@user"): "pass123"}
