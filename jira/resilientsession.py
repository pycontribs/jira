# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from requests import Session
from requests.exceptions import ConnectionError
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):

        def emit(self, record):
            pass
import random
import time
import json
from .exceptions import JIRAError

logging.getLogger('jira').addHandler(NullHandler())


def _is_invalid_jra41559_response(response):
    """
    Detect invalid responses caused by https://jira.atlassian.com/browse/JRA-41559
    
    See also https://answers.atlassian.com/questions/11457054/answers/11975162
    """
    return response.status_code == 200 and len(response.content) == 0 \
        and 'X-Seraph-LoginReason' in response.headers \
        and 'AUTHENTICATED_FAILED' in response.headers['X-Seraph-LoginReason']

def raise_on_error(r, verb='???', **kwargs):
    request = kwargs.get('request', None)
    # headers = kwargs.get('headers', None)

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


class ResilientSession(Session):

    """
    This class is supposed to retry requests that do return temporary errors.

    At this moment it supports: 502, 503, 504
    """

    def __init__(self):
        self.max_retries = 3
        super(ResilientSession, self).__init__()

        # Indicate our preference for JSON to avoid https://bitbucket.org/bspeakmon/jira-python/issue/46 and https://jira.atlassian.com/browse/JRA-38551
        self.headers.update({"Accept": "application/json,*.*;q=0.9"})

    def __recoverable(self, response, url, request, counter=1):
        msg = response
        if isinstance(response, ConnectionError):
            logging.warning("Got ConnectionError [%s] errno:%s on %s %s\n%s\%s" % (
                response, response.errno, request, url, vars(response), response.__dict__))
        if hasattr(response, 'status_code'):
            if response.status_code in [502, 503, 504]:
                msg = "%s %s" % (response.status_code, response.reason)
            elif _is_invalid_jra41559_response(response):
                msg = "Atlassian's bug https://jira.atlassian.com/browse/JRA-41559"
            else:
                # This error cannot be retried
                return False
    
        # Exponential backoff with full jitter.
        delay = min(60, 10 * 2 ** counter) * random.random()
        logging.warning("Got recoverable error from %s %s, will retry [%s/%s] in %ss. Err: %s" % (
            request, url, counter, self.max_retries, delay, msg))
        time.sleep(delay)
        return True

    def __verb(self, verb, url, retry_data=None, **kwargs):

        d = self.headers.copy()
        d.update(kwargs.get('headers', {}))
        kwargs['headers'] = d

        # if we pass a dictionary as the 'data' we assume we want to send json
        # data
        data = kwargs.get('data', {})
        if isinstance(data, dict):
            data = json.dumps(data)

        retry_number = 0
        while retry_number <= self.max_retries:
            response = None
            exception = None
            try:
                method = getattr(super(ResilientSession, self), verb.lower())
                response = method(url, **kwargs)
                if response.status_code == 200 and not _is_invalid_jra41559_response(response):
                    return response
            except ConnectionError as e:
                logging.warning(
                    "%s while doing %s %s [%s]" % (e, verb.upper(), url, kwargs))
                exception = e
            retry_number += 1

            if retry_number <= self.max_retries:
                response_or_exception = response if response is not None else exception
                if self.__recoverable(response_or_exception, url, verb.upper(), retry_number):
                    if retry_data:
                        # if data is a stream, we cannot just read again from it,
                        # retry_data() will give us a new stream with the data
                        kwargs['data'] = retry_data()
                    continue
                else:
                    break

        if exception is not None:
            raise exception
        raise_on_error(response, verb=verb, **kwargs)
        return response

    def get(self, url, **kwargs):
        return self.__verb('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.__verb('POST', url, **kwargs)

    def put(self, url, **kwargs):
        return self.__verb('PUT', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.__verb('DELETE', url, **kwargs)

    def head(self, url, **kwargs):
        return self.__verb('HEAD', url, **kwargs)

    def patch(self, url, **kwargs):
        return self.__verb('PATCH', url, **kwargs)

    def options(self, url, **kwargs):
        return self.__verb('OPTIONS', url, **kwargs)
