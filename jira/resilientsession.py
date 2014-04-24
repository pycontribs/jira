from requests import Session
import logging
import time


class ResilientSession(Session):

    """
    This class is supposed to retry requests that do return temporary errors.

    At this moment it supports: 502, 503, 504
    """

    def __recoverable(self, r, url, request, counter=1):
        if r.status_code in [502, 503, 504]:
            DELAY = 10 * counter
            logging.warn("Got recoverable error [%s] from %s %s, retry #%s in %ss" % (r.status_code, request, url, counter, DELAY))
            time.sleep(DELAY)
            return True
        return False

    def get(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).get(url, **kwargs)
            if self.__recoverable(r, url, 'GET', counter):
                continue
            return r

    def post(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).post(url, **kwargs)
            if self.__recoverable(r, url, 'POST', counter):
                continue
            return r

    def delete(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).delete(url, **kwargs)
            if self.__recoverable(r, url, 'DELETE', counter):
                continue
            return r

    def put(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).put(url, **kwargs)
            if self.__recoverable(r, url, 'PUT', counter):
                continue
            return r

    def head(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).head(url, **kwargs)
            if self.__recoverable(r, url, 'HEAD', counter):
                continue
            return r

    def patch(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).patch(url, **kwargs)
            if self.__recoverable(r, url, 'PATCH', counter):
                continue
            return r

    def options(self, url, **kwargs):
        counter = 0
        while True:
            counter += 1
            r = super(ResilientSession, self).options(url, **kwargs)
            if self.__recoverable(r, url, 'OPTIONS', counter):
                continue
            return r
