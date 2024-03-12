"""Jira utils used internally."""

from __future__ import annotations

import functools
import threading
import warnings
from typing import Any, Callable, cast

from requests import Response
from requests.structures import CaseInsensitiveDict as _CaseInsensitiveDict

from jira.exceptions import JIRAError
from jira.resilientsession import raise_on_error


class CaseInsensitiveDict(_CaseInsensitiveDict):
    """A case-insensitive ``dict``-like object.

    DEPRECATED: use requests.structures.CaseInsensitiveDict directly.

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
    operations are given keys that have equal ``.lower()`` s, the
    behavior is undefined.

    """

    def __init__(self, *args, **kwargs) -> None:
        warnings.warn(
            "Use requests.structures.CaseInsensitiveDict directly", DeprecationWarning
        )
        super().__init__(*args, **kwargs)


def threaded_requests(requests):
    for fn, url, request_args in requests:
        th = threading.Thread(target=fn, args=(url,), kwargs=request_args, name=url)
        th.start()

    for th in threading.enumerate():
        if th.name.startswith("http"):
            th.join()


def json_loads(resp: Response | None) -> Any:
    """Attempts to load json the result of a response.

    Args:
        resp (Optional[Response]): The Response object

    Raises:
        JIRAError: via :py:func:`jira.resilientsession.raise_on_error`

    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: the json
    """
    raise_on_error(resp)  # if 'resp' is None, will raise an error here
    resp = cast(Response, resp)  # tell mypy only Response-like are here
    try:
        return resp.json()
    except ValueError:
        # json.loads() fails with empty bodies
        if not resp.text:
            return {}
        raise


def cloud(client_method: Callable) -> Callable:
    """A convenience decorator to check if the Jira instance is cloud.

    Checks if the client instance is talking to Cloud Jira. If it is, return
    the result of the called client method. If not, return None and log a
    warning.

    Args:
      client_method: The method that is being called by the client.

    Returns:
      Either the result of the wrapped function or None.
    """

    @functools.wraps(client_method)
    def check_if_cloud(*args, **kwargs):
        # NOTE(jpavlav): The first argument of any class instance is a `self`
        # reference. Avoiding magic numbers here.
        instance = next(arg for arg in args)
        if instance._is_cloud:
            return client_method(*args, **kwargs)

        instance.log.warning(
            "This functionality is not available on Jira Data Center (Server) version."
        )
        return None

    return check_if_cloud


def experimental(client_method: Callable) -> Callable:
    """A convenience decorator to inform if a client method is experimental.

    Indicates the path covered by the client method is experimental. If the path
    disappears or the method becomes disallowed, this logs an error and returns
    None. If another kind of exception is raised, this reraises.

    Raises:
      JIRAError: In the case the error is not an HTTP error with a status code.

    Returns:
      Either the result of the wrapped function or None.
    """

    @functools.wraps(client_method)
    def is_experimental(*args, **kwargs):
        instance = next(arg for arg in args)

        try:
            return client_method(*args, **kwargs)
        except JIRAError as e:
            response = getattr(e, "response", None)
            if response is not None and response.status_code in [405, 404]:
                instance.log.warning(
                    f"Functionality at path {response.url} is/was experimental. "
                    f"Status Code: {response.status_code}"
                )
                return None
            else:
                raise

    return is_experimental


def remove_empty_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """A convenience function to remove key/value pairs with `None` for a value.

    Args:
      data: A dictionary.

    Returns:
      Dict[str, Any]: A dictionary with no `None` key/value pairs.
    """
    return {key: val for key, val in data.items() if val is not None}
