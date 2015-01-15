# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from requests import Session
from requests.exceptions import ConnectionError
from .utils import raise_on_error
import logging
import time
import json


MAX_RETRIES = 3


class ResilientSession(Session):

    """
    This class is supposed to retry requests that do return temporary errors.

    At this moment it supports: 502, 503, 504
    """

    def __recoverable(self, response, url, request, counter=1):
        if type(response) == ConnectionError:
            logging.warn("Got ConnectionError [%s] errno:%s on %s %s\n%s\%s" % (
                response, response.errno, request, url, vars(response), response.__dict__))
        if hasattr(response, 'status_code'):
            if response.status_code in [502, 503, 504]:
                return True
            elif response.status_code == 200 and \
                    len(response.text) == 0 and \
                    'X-Seraph-LoginReason' in response.headers and \
                    'AUTHENTICATED_FAILED' in response.headers['X-Seraph-LoginReason']:
                logging.warning(
                    "Detected Atlassian bug https://jira.atlassian.com/browse/JRA-41559 ...")
                return True
            else:
                return False

        DELAY = 10 * counter
        logging.warn("Got recoverable error [%s] from %s %s, retry #%s in %ss" % (
            response, request, url, counter, DELAY))
        time.sleep(DELAY)
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
        while counter < MAX_RETRIES:
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
