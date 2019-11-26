# -*- coding: utf-8 -*-
"""JIRA utils used internally."""
import threading

from jira.resilientsession import raise_on_error


class CaseInsensitiveDict(dict):
    """A case-insensitive ``dict``-like object.

    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['accept'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.

    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.

    """

    def __init__(self, *args, **kw):
        super(CaseInsensitiveDict, self).__init__(*args, **kw)

        upper_keys_list = []
        for key in super(CaseInsensitiveDict, self).keys():
            if key != key.lower():
                upper_keys_list.append(key)

        for upper_key in upper_keys_list:
            self[upper_key.lower()] = self[upper_key]
            self.pop(upper_key, None)

    def __setitem__(self, key, value):
        """Overwrite [] implementation."""
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
        th = threading.Thread(target=fn, args=(url,), kwargs=request_args, name=url)
        th.start()

    for th in threading.enumerate():
        if th.name.startswith("http"):
            th.join()


def json_loads(r):
    raise_on_error(r)
    try:
        return r.json()
    except ValueError:
        # json.loads() fails with empty bodies
        if not r.text:
            return {}
        raise
