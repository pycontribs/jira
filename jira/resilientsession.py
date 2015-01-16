# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from requests import Session
from requests.exceptions import ConnectionError
from .utils import raise_on_error
import logging
import time
import json


class ResilientSession(Session):

    """
    This class is supposed to retry requests that do return temporary errors.

    At this moment it supports: 502, 503, 504
    """

    def __init__(self):
        self.max_retries = 3
        super(ResilientSession, self).__init__()

    def __recoverable(self, response, url, request, counter=1):
        msg = response
        if type(response) == ConnectionError:
            logging.warn("Got ConnectionError [%s] errno:%s on %s %s\n%s\%s" % (
                response, response.errno, request, url, vars(response), response.__dict__))
        if hasattr(response, 'status_code'):
            if response.status_code in [502, 503, 504]:
                return True
            elif not (response.status_code == 200 and
                      len(response.text) == 0 and
                      'X-Seraph-LoginReason' in response.headers and
                      'AUTHENTICATED_FAILED' in response.headers['X-Seraph-LoginReason']):
                return False
            else:
                msg = "Atlassian's bug https://jira.atlassian.com/browse/JRA-41559"

        delay = 10 * counter
        logging.warn("Got recoverable error from %s %s, will retry [%s/%s] in %ss. Err: %s" % (
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

        counter = 0
        while counter < self.max_retries:
            counter += 1
            try:
                method = getattr(super(ResilientSession, self), verb.lower())\

                r = method(url, **kwargs)
            except ConnectionError as e:
                logging.warning(
                    "%s while doing %s %s [%s]" % (e, verb.upper(), url, kwargs))
                r = e
            if self.__recoverable(r, url, verb.upper(), counter):
                if retry_data:
                    # if data is a stream, we cannot just read again from it,
                    # retry_data() will give us a new stream with the data
                    kwargs['data'] = retry_data()
                continue
            raise_on_error(r, verb=verb, **kwargs)
            return r

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
