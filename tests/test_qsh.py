# -*- coding: utf-8 -*-
import pytest
from jira.client import QshGenerator


class MockRequest(object):
    def __init__(self, method, url):
        self.method = method
        self.url = url


@pytest.mark.parametrize(
    "method,url,expected",
    [
        ("GET", "http://example.com", "GET&&"),
        # empty parameter
        ("GET", "http://example.com?key=&key2=A", "GET&&key=&key2=A"),
        # whitespace
        ("GET", "http://example.com?key=A+B", "GET&&key=A%20B"),
        # tilde
        ("GET", "http://example.com?key=A~B", "GET&&key=A~B"),
        # repeated parameters
        (
            "GET",
            "http://example.com?key2=Z&key1=X&key3=Y&key1=A",
            "GET&&key1=A,X&key2=Z&key3=Y",
        ),
        # repeated parameters with whitespace
        (
            "GET",
            "http://example.com?key2=Z+A&key1=X+B&key3=Y&key1=A+B",
            "GET&&key1=A%20B,X%20B&key2=Z%20A&key3=Y",
        ),
    ],
    ids=[
        "no parameters",
        "empty parameter",
        "whitespace",
        "tilde",
        "repeated parameters",
        "repeated parameters with whitespace",
    ],
)
def test_qsh(method, url, expected):
    gen = QshGenerator("http://example.com")
    req = MockRequest(method, url)
    assert gen._generate_qsh(req) == expected
