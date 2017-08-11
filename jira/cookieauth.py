#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

"""
This module implements cookie based authentication, which can be used to avoid
a problem where JIRA can become unresponsive under great volume of HTTP basic
auth requests (https://jira.atlassian.com/browse/JRASERVER-26397)
"""

import json
import datetime

import requests
from requests.auth import AuthBase



class JIRACookieAuth(AuthBase):
    """ JIRA specific cookie authentication """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.last_refresh = None
        self.check_interval = datetime.timedelta(minutes=5)
        self.cookies = None

    def login(self, req):
        server = req.url.replace(req.path_url, '')
        login_url = "{}/rest/auth/1/session".format(server)
        login_data = {'username': self.username, 'password': self.password}

        session = requests.Session()
        r = session.post(login_url,
                         data=json.dumps(login_data),
                         headers={'Content-Type': 'application/json'})

        self.cookies = r.cookies
        self.last_refresh = datetime.datetime.now()

    def __call__(self, req):
        if self.last_refresh is None:
            self.login(req)
        elif  datetime.datetime.now() > self.last_refresh + self.check_interval:
            self.login(req)

        # clean up, since we can't generate new cookies otherwise
        if 'Cookie' in req.headers:
            del req.headers['Cookie']

        # add other auth-related tokens if they don't exist
        if 'X-Atlassian-Token' not in req.headers:
            req.headers['X-Atlassian-Token'] = 'no-check'

        req.prepare_cookies(self.cookies)
        return req
