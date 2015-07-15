# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import threading
import json
import logging


class CaseInsensitiveDict(dict):

    """
    A case-insensitive ``dict``-like object.

    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
C
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.

    """

    def __init__(self, *args, **kw):
        super(CaseInsensitiveDict, self).__init__(*args, **kw)

        self.itemlist = {}
        for key, value in super(CaseInsensitiveDict, self).items():
            if key != key.lower():
                self[key.lower()] = value
                self.pop(key, None)

        #self.itemlist[key.lower()] = value

    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    # def __iter__(self):
    #    return iter(self.itemlist)

    # def keys(self):
    #    return self.itemlist

    # def values(self):
    #    return [self[key] for key in self]

    # def itervalues(self):
    #    return (self[key] for key in self)


def threaded_requests(requests):
    for fn, url, request_args in requests:
        th = threading.Thread(
            target=fn, args=(url,), kwargs=request_args, name=url,
        )
        th.start()

    for th in threading.enumerate():
        if th.name.startswith('http'):
            th.join()


def json_loads(r):
    raise_on_error(r)
    if len(r.text):  # r.status_code != 204:
        return json.loads(r.text)
    else:
        # json.loads() fails with empy bodies
        return {}


def raise_on_error(r, verb='???', **kwargs):
    request = kwargs.get('request', None)
    headers = kwargs.get('headers', None)

    if r is None:
        raise JIRAError(None, **kwargs)

    if r.status_code >= 400:
        error = ''
        if r.status_code == 403 and "x-authentication-denied-reason" in r.headers:
            error = r.headers["x-authentication-denied-reason"]
        elif r.text:
            try:
                response = json.loads(r.text)
                if 'message' in response:
                    # JIRA 5.1 errors
                    error = response['message']
                elif 'errorMessages' in response and len(response['errorMessages']) > 0:
                    # JIRA 5.0.x error messages sometimes come wrapped in this array
                    # Sometimes this is present but empty
                    errorMessages = response['errorMessages']
                    if isinstance(errorMessages, (list, tuple)):
                        error = errorMessages[0]
                    else:
                        error = errorMessages
                elif 'errors' in response and len(response['errors']) > 0:
                    # JIRA 6.x error messages are found in this array.
                    error_list = response['errors'].values()
                    error = ", ".join(error_list)
                else:
                    error = r.text
            except ValueError:
                error = r.text
        raise JIRAError(
            r.status_code, error, r.url, request=request, response=r, **kwargs)
    # for debugging weird errors on CI
    if r.status_code not in [200, 201, 202, 204]:
        raise JIRAError(r.status_code, request=request, response=r, **kwargs)
    # testing for the WTH bug exposed on
    # https://answers.atlassian.com/questions/11457054/answers/11975162
    if r.status_code == 200 and len(r.text) == 0 \
            and 'X-Seraph-LoginReason' in r.headers \
            and 'AUTHENTICATED_FAILED' in r.headers['X-Seraph-LoginReason']:
        pass


class JIRAError(Exception):

    """General error raised for all problems in operation of the client."""

    def __init__(self, status_code=None, text=None, url=None, request=None, response=None, **kwargs):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.request = request
        self.response = response
        self.headers = kwargs.get('headers', None)

    def __str__(self):
        t = "JiraError HTTP %s" % self.status_code
        if self.text:
            t += "\n\ttext: %s" % self.text
        if self.url:
            t += "\n\turl: %s" % self.url

        if self.request is not None and hasattr(self.request, 'headers'):
            t += "\n\trequest headers = %s" % self.request.headers

        if self.request is not None and hasattr(self.request, 'text'):
            t += "\n\trequest text = %s" % self.request.text

        if self.response is not None and hasattr(self.response, 'headers'):
            t += "\n\tresponse headers = %s" % self.response.headers

        if self.response is not None and hasattr(self.response, 'text'):
            t += "\n\tresponse text = %s" % self.response.text

        t += '\n'
        return t


def get_error_list(r):
    error_list = []
    if r.status_code >= 400:
        if r.status_code == 403 and "x-authentication-denied-reason" in r.headers:
            error_list = [r.headers["x-authentication-denied-reason"]]
        elif r.text:
            try:
                response = json_loads(r)
                if 'message' in response:
                    # JIRA 5.1 errors
                    error_list = [response['message']]
                elif 'errorMessages' in response and len(response['errorMessages']) > 0:
                    # JIRA 5.0.x error messages sometimes come wrapped in this array
                    # Sometimes this is present but empty
                    errorMessages = response['errorMessages']
                    if isinstance(errorMessages, (list, tuple)):
                        error_list = errorMessages
                    else:
                        error_list = [errorMessages]
                elif 'errors' in response and len(response['errors']) > 0:
                    # JIRA 6.x error messages are found in this array.
                    error_list = response['errors'].values()
                else:
                    error_list = [r.text]
            except ValueError:
                error_list = [r.text]
    return error_list
