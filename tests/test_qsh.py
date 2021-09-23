# -*- coding: utf-8 -*-
import getpass

import pytest

from jira.client import QshGenerator
from jira.exceptions import JIRAError
from tests.conftest import JiraTestManager, get_unique_project_name

class MockRequest(object):
    def __init__(self, method, url):
        self.method = method
        self.url = url

def test_qsh():
    gen = QshGenerator("http://example.com")

    for method, url, expected in [("GET", "http://example.com", "GET&&"),
                                  # whitesapce
                                  ("GET", "http://example.com/path?key=A+B", "GET&&key=A%20B"),
                                  # repeated parameters
                                  ("GET", "http://example.com/path?key2=Z&key1=X&key3=Y&key1=A", "GET&&key1=A,X&key2=Z&key3=Y"),
                                  # repeated parameters with whitepsace
                                  ("GET", "http://example.com/path?key2=Z+A&key1=X+B&key3=Y&key1=A+B", "GET&&key1=A%20B,X%20B&key2=Z%20A&key3=Y")]:

        req = MockRequest(method, url)
        assert(gen._generate_qsh(req) == expected)
