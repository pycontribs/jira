# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest  # noqa
import requests  # noqa
import sys

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
except ImportError:
    from mock import patch

from jira import Role, Issue, JIRA, JIRAError, Project  # noqa
import jira.jirashell as jirashell


def test_unicode(requests_mock, capsys):
    """This functions tests that CLI tool does not throw an UnicodeDecodeError
    when it attempts to display some Unicode error message, which can happen
    when printing exceptions received from the remote HTTP server.

    Introduce for catching py2 Unicode output workaround regression.
    Likely not needed for Py3 versions.
    """
    requests_mock.register_uri('GET', 'http://localhost/rest/api/2/serverInfo', text='Δεν βρέθηκε', status_code=404)
    testargs = ["jirashell", "-s", "http://localhost"]
    with patch.object(sys, 'argv', testargs):
        jirashell.main()
    captured = capsys.readouterr()
    assert captured.err.startswith("JiraError HTTP 404")
    assert captured.out == ""
