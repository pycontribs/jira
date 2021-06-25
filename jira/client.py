#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This module implements a friendly (well, friendlier) interface between the raw JSON
responses from Jira and the Resource/dict abstractions provided by this library. Users
will construct a JIRA object as described below. Full API documentation can be found
at: https://jira.readthedocs.io/en/latest/
"""
import calendar
import copy
import datetime
import hashlib
import imghdr
import json
import logging as _logging
import mimetypes
import os
import re
import sys
import time
import warnings
from collections import OrderedDict
from collections.abc import Iterable
from functools import lru_cache, wraps
from io import BufferedReader
from numbers import Number
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    no_type_check,
)
from urllib.parse import urlparse

import requests
from pkg_resources import parse_version
from requests import Response
from requests.auth import AuthBase
from requests.utils import get_netrc_auth

from jira import __version__

# GreenHopper specific resources
from jira.exceptions import JIRAError
from jira.resilientsession import ResilientSession, raise_on_error

# Jira-specific resources
from jira.resources import (
    Attachment,
    Board,
    Comment,
    Component,
    Customer,
    CustomFieldOption,
    Dashboard,
    Filter,
    GreenHopperResource,
    Group,
    Issue,
    IssueLink,
    IssueLinkType,
    IssueType,
    Priority,
    Project,
    RemoteLink,
    RequestType,
    Resolution,
    Resource,
    Role,
    SecurityLevel,
    ServiceDesk,
    Sprint,
    Status,
    StatusCategory,
    User,
    Version,
    Votes,
    Watchers,
    Worklog,
)
from jira.utils import CaseInsensitiveDict, json_loads, threaded_requests

try:
    # noinspection PyUnresolvedReferences
    from requests_toolbelt import MultipartEncoder
except ImportError:
    pass

try:
    from requests_jwt import JWTAuth
except ImportError:
    pass


LOG = _logging.getLogger("jira")
LOG.addHandler(_logging.NullHandler())


def translate_resource_args(func: Callable):
    """Decorator that converts Issue and Project resources to their keys when used as arguments."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        arg_list = []
        for arg in args:
            if isinstance(arg, (Issue, Project)):
                arg_list.append(arg.key)
            else:
                arg_list.append(arg)
        result = func(*arg_list, **kwargs)
        return result

    return wrapper


def _field_worker(
    fields: Dict[str, Any] = None, **fieldargs: Any
) -> Union[Dict[str, Dict[str, Any]], Dict[str, Dict[str, str]]]:
    if fields is not None:
        return {"fields": fields}
    return {"fields": fieldargs}


ResourceType = TypeVar("ResourceType", contravariant=True, bound=Resource)


class ResultList(list, Generic[ResourceType]):
    def __init__(
        self,
        iterable: Iterable = None,
        _startAt: int = 0,
        _maxResults: int = 0,
        _total: Optional[int] = None,
        _isLast: Optional[bool] = None,
    ) -> None:
        """

        Args:
            iterable (Iterable): [description]. Defaults to None.
            _startAt (int): Start page. Defaults to 0.
            _maxResults (int): Max results per page. Defaults to 0.
            _total (Optional[int]): Total results from query. Defaults to 0.
            _isLast (Optional[bool]): Last Page? Defaults to None.
        """
        if iterable is not None:
            list.__init__(self, iterable)
        else:
            list.__init__(self)

        self.startAt = _startAt
        self.maxResults = _maxResults
        # Optional parameters:
        self.isLast = _isLast
        self.total = _total if _total is not None else len(self)

        self.iterable: List = list(iterable) if iterable else []
        self.current = self.startAt

    def __next__(self) -> Type[ResourceType]:
        self.current += 1
        if self.current > self.total:
            raise StopIteration
        else:
            return self.iterable[self.current - 1]


class QshGenerator(object):
    def __init__(self, context_path):
        self.context_path = context_path

    def __call__(self, req):
        parse_result = urlparse(req.url)

        path = (
            parse_result.path[len(self.context_path) :]
            if len(self.context_path) > 1
            else parse_result.path
        )
        # Per Atlassian docs, use %20 for whitespace when generating qsh for URL
        # https://developer.atlassian.com/cloud/jira/platform/understanding-jwt/#qsh
        query = "&".join(sorted(parse_result.query.split("&"))).replace("+", "%20")
        qsh = f"{req.method.upper()}&{path}&{query}"

        return hashlib.sha256(qsh.encode("utf-8")).hexdigest()


class JiraCookieAuth(AuthBase):
    """Jira Cookie Authentication

    Allows using cookie authentication as described by
    https://developer.atlassian.com/jiradev/jira-apis/jira-rest-apis/jira-rest-api-tutorials/jira-rest-api-example-cookie-based-authentication

    """

    def __init__(
        self, session: ResilientSession, _get_session: Callable, auth: Tuple[str, str]
    ):
        """Cookie Based Authentication

        Args:
            session (ResilientSession): The Session object to communicate with the API.
            _get_session (Callable): The function that returns a :py_class:``User``
            auth (Tuple[str, str]): The username, password tuple
        """
        self._session = session
        self._get_session = _get_session
        self.__auth = auth

    def handle_401(self, response, **kwargs):
        if response.status_code != 401:
            return response
        self.init_session()
        response = self.process_original_request(response.request.copy())
        return response

    def process_original_request(self, original_request):
        self.update_cookies(original_request)
        return self.send_request(original_request)

    def update_cookies(self, original_request):
        # Cookie header needs first to be deleted for the header to be updated using
        # the prepare_cookies method. See request.PrepareRequest.prepare_cookies
        if "Cookie" in original_request.headers:
            del original_request.headers["Cookie"]
        original_request.prepare_cookies(self.cookies)

    def init_session(self):
        self.start_session()

    def __call__(self, request):
        request.register_hook("response", self.handle_401)
        return request

    def send_request(self, request):
        return self._session.send(request)

    @property
    def cookies(self):
        return self._session.cookies

    def start_session(self):
        self._get_session(self.__auth)


class JIRA(object):
    """User interface to Jira.

    Clients interact with Jira by constructing an instance of this object and calling its methods. For addressable
    resources in Jira -- those with "self" links -- an appropriate subclass of :py:class:`jira.resources.Resource` will be returned
    with customized ``update()`` and ``delete()`` methods, along with attribute access to fields. This means that calls
    of the form ``issue.fields.summary`` will be resolved into the proper lookups to return the JSON value at that
    mapping. Methods that do not return resources will return a dict constructed from the JSON response or a scalar
    value; see each method's documentation for details on what that method returns.

    Without any arguments, this client will connect anonymously to the Jira instance
    started by the Atlassian Plugin SDK from one of the 'atlas-run', ``atlas-debug``,
    or ``atlas-run-standalone`` commands. By default, this instance runs at
    ``http://localhost:2990/jira``. The ``options`` argument can be used to set the Jira instance to use.

    Authentication is handled with the ``basic_auth`` argument. If authentication is supplied (and is
    accepted by Jira), the client will remember it for subsequent requests.

    For quick command line access to a server, see the ``jirashell`` script included with this distribution.

    The easiest way to instantiate is using ``j = JIRA("https://jira.atlassian.com")``
    """

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "auth_url": "/rest/auth/1/session",
        "context_path": "/",
        "rest_path": "api",
        "rest_api_version": "2",
        "agile_rest_path": GreenHopperResource.GREENHOPPER_REST_PATH,
        "agile_rest_api_version": "1.0",
        "verify": True,
        "resilient": True,
        "async": False,
        "async_workers": 5,
        "client_cert": None,
        "check_update": False,
        # amount of seconds to wait for loading a resource after updating it
        # used to avoid server side caching issues, used to be 4 seconds.
        "delay_reload": 0,
        "headers": {
            "Cache-Control": "no-cache",
            # 'Accept': 'application/json;charset=UTF-8',  # default for REST
            "Content-Type": "application/json",  # ;charset=UTF-8',
            # 'Accept': 'application/json',  # default for REST
            # 'Pragma': 'no-cache',
            # 'Expires': 'Thu, 01 Jan 1970 00:00:00 GMT'
            "X-Atlassian-Token": "no-check",
        },
    }

    checked_version = False

    # TODO(ssbarnea): remove these two variables and use the ones defined in resources
    JIRA_BASE_URL = Resource.JIRA_BASE_URL
    AGILE_BASE_URL = GreenHopperResource.AGILE_BASE_URL

    def __init__(
        self,
        server: str = None,
        options: Dict[str, Union[str, bool, Any]] = None,
        basic_auth: Union[None, Tuple[str, str]] = None,
        oauth: Dict[str, Any] = None,
        jwt: Dict[str, Any] = None,
        kerberos=False,
        kerberos_options: Dict[str, Any] = None,
        validate=False,
        get_server_info: bool = True,
        async_: bool = False,
        async_workers: int = 5,
        logging: bool = True,
        max_retries: int = 3,
        proxies: Any = None,
        timeout: Optional[Union[Union[float, int], Tuple[float, float]]] = None,
        auth: Tuple[str, str] = None,
    ):
        """Construct a Jira client instance.

        Without any arguments, this client will connect anonymously to the Jira instance
        started by the Atlassian Plugin SDK from one of the 'atlas-run', ``atlas-debug``,
        or ``atlas-run-standalone`` commands. By default, this instance runs at
        ``http://localhost:2990/jira``. The ``options`` argument can be used to set the Jira instance to use.

        Authentication is handled with the ``basic_auth`` argument. If authentication is supplied (and is
        accepted by Jira), the client will remember it for subsequent requests.

        For quick command line access to a server, see the ``jirashell`` script included with this distribution.

        The easiest way to instantiate is using ``j = JIRA("https://jira.atlasian.com")``

        Args:
            server (Optional[str]): The server address and context path to use. Defaults to ``http://localhost:2990/jira``.
            options (Optional[Dict[str, Any]]): Specify the server and properties this client will use.
              Use a dict with any of the following properties:

                * server -- the server address and context path to use. Defaults to ``http://localhost:2990/jira``.
                * rest_path -- the root REST path to use. Defaults to ``api``, where the Jira REST resources live.
                * rest_api_version -- the version of the REST resources under rest_path to use. Defaults to ``2``.
                * agile_rest_path - the REST path to use for Jira Agile requests. Defaults to ``greenhopper`` (old, private
                  API). Check :py:class:`jira.resources.GreenHopperResource` for other supported values.
                * verify -- Verify SSL certs. Defaults to ``True``.
                * client_cert -- a tuple of (cert,key) for the requests library for client side SSL
                * check_update -- Check whether using the newest python-jira library version.

            basic_auth (Union[None, Tuple[str, str]]): A tuple of username and password to use when
              establishing a session via HTTP BASIC authentication.
            oauth (Optional[Any]): A dict of properties for OAuth authentication. The following properties are required:

                * access_token -- OAuth access token for the user
                * access_token_secret -- OAuth access token secret to sign with the key
                * consumer_key -- key of the OAuth application link defined in Jira
                * key_cert -- private key file to sign requests with (should be the pair of the public key supplied to
                  Jira in the OAuth application link)

            kerberos (bool): If true it will enable Kerberos authentication.
            kerberos_options (Optional[Dict[str,str]]): A dict of properties for Kerberos authentication.
              The following properties are possible:

                * mutual_authentication -- string DISABLED or OPTIONAL.

                Example kerberos_options structure: ``{'mutual_authentication': 'DISABLED'}``

            jwt (Optional[Any]): A dict of properties for JWT authentication supported by Atlassian Connect.
              The following properties are required:

                * secret -- shared secret as delivered during 'installed' lifecycle event
                  (see https://developer.atlassian.com/static/connect/docs/latest/modules/lifecycle.html for details)
                * payload -- dict of fields to be inserted in the JWT payload, e.g. 'iss'

                Example jwt structure: ``{'secret': SHARED_SECRET, 'payload': {'iss': PLUGIN_KEY}}``

            validate (bool): If true it will validate your credentials first. Remember that if you are accessing Jira
              as anonymous it will fail to instantiate.
            get_server_info (bool): If true it will fetch server version info first to determine if some API calls
              are available.
            async_ (bool): To enable async requests for those actions where we implemented it, like issue update() or delete().
            async_workers (int): Set the number of worker threads for async operations.
            timeout (Optional[Union[Union[float, int], Tuple[float, float]]]): Set a read/connect timeout for the underlying
              calls to Jira (default: None).
              Obviously this means that you cannot rely on the return code when this is enabled.
            max_retries (int): Sets the amount Retries for the HTTP sessions initiated by the client. (Default: 3)
            proxies (Optional[Any]): Sets the proxies for the HTTP session.
            auth (Optional[Tuple[str,str]]): Set a cookie auth token if this is required.
            logging (bool): Determine whether or not logging should be enabled. (Default: True)
        """
        # force a copy of the tuple to be used in __del__() because
        # sys.version_info could have already been deleted in __del__()
        self.sys_version_info = tuple([i for i in sys.version_info])

        if options is None:
            options = {}
            if server and isinstance(server, dict):
                warnings.warn(
                    "Old API usage, use JIRA(url) or JIRA(options={'server': url}, when using dictionary always use named parameters.",
                    DeprecationWarning,
                )
                options = server
                server = ""

        if server:
            options["server"] = server
        if async_:
            options["async"] = async_
            options["async_workers"] = async_workers

        LOG.setLevel(_logging.INFO if logging else _logging.CRITICAL)
        self.log = LOG

        self._options: Dict[str, Any] = copy.copy(JIRA.DEFAULT_OPTIONS)

        self._options.update(options)

        self._rank = None

        # Rip off trailing slash since all urls depend on that
        assert isinstance(self._options["server"], str)  # to help mypy
        if self._options["server"].endswith("/"):
            self._options["server"] = self._options["server"][:-1]

        context_path = urlparse(self.server_url).path
        if len(context_path) > 0:
            self._options["context_path"] = context_path

        self._try_magic()

        assert isinstance(self._options["headers"], dict)  # for mypy benefit
        self._session: ResilientSession  # for mypy benefit
        if oauth:
            self._create_oauth_session(oauth, timeout)
        elif basic_auth:
            self._create_http_basic_session(*basic_auth, timeout=timeout)
            self._session.headers.update(self._options["headers"])
        elif jwt:
            self._create_jwt_session(jwt, timeout)
        elif kerberos:
            self._create_kerberos_session(timeout, kerberos_options=kerberos_options)
        elif auth:
            self._create_cookie_auth(auth, timeout)
            # always log in for cookie based auth, as we need a first request to be logged in
            validate = True
        else:
            verify = bool(self._options["verify"])
            self._session = ResilientSession(timeout=timeout)
            self._session.verify = verify

        self._session.headers.update(self._options["headers"])

        if "cookies" in self._options:
            self._session.cookies.update(self._options["cookies"])

        self._session.max_retries = max_retries

        if proxies:
            self._session.proxies = proxies

        self.auth = auth
        if validate:
            # This will raise an Exception if you are not allowed to login.
            # It's better to fail faster than later.
            user = self.session()
            if user.raw is None:
                auth_method = (
                    oauth or basic_auth or jwt or kerberos or auth or "anonymous"
                )
                raise JIRAError(f"Can not log in with {str(auth_method)}")

        self.deploymentType = None
        if get_server_info:
            # We need version in order to know what API calls are available or not
            si = self.server_info()
            try:
                self._version = tuple(si["versionNumbers"])
            except Exception as e:
                self.log.error("invalid server_info: %s", si)
                raise e
            self.deploymentType = si.get("deploymentType")
        else:
            self._version = (0, 0, 0)

        if self._options["check_update"] and not JIRA.checked_version:
            self._check_update_()
            JIRA.checked_version = True

        self._fields = {}
        for f in self.fields():
            if "clauseNames" in f:
                for name in f["clauseNames"]:
                    self._fields[name] = f["id"]

    @property
    def server_url(self) -> str:
        """Return the server url"""
        return str(self._options["server"])

    @property
    def _is_cloud(self) -> bool:
        """Return whether we are on a Cloud based Jira instance."""
        return self.deploymentType in ("Cloud",)

    def _create_cookie_auth(
        self,
        auth: Tuple[str, str],
        timeout: Optional[Union[Union[float, int], Tuple[float, float]]],
    ):
        self._session = ResilientSession(timeout=timeout)
        self._session.auth = JiraCookieAuth(self._session, self.session, auth)
        self._session.verify = bool(self._options["verify"])
        client_cert: Tuple[str, str] = self._options["client_cert"]  # to help mypy
        self._session.cert = client_cert

    def _check_update_(self):
        """Check if the current version of the library is outdated."""
        try:
            data = requests.get(
                "https://pypi.python.org/pypi/jira/json", timeout=2.001
            ).json()

            released_version = data["info"]["version"]
            if parse_version(released_version) > parse_version(__version__):
                warnings.warn(
                    "You are running an outdated version of Jira Python %s. Current version is %s. Do not file any bugs against older versions."
                    % (__version__, released_version)
                )
        except requests.RequestException:
            pass
        except Exception as e:
            self.log.warning(e)

    def __del__(self):
        """Destructor for JIRA instance."""
        self.close()

    def close(self):
        session = getattr(self, "_session", None)
        if session is not None:
            try:
                session.close()
            except TypeError:
                # TypeError: "'NoneType' object is not callable"
                # Could still happen here because other references are also
                # in the process to be torn down, see warning section in
                # https://docs.python.org/2/reference/datamodel.html#object.__del__
                pass
            self._session = None

    def _check_for_html_error(self, content: str):
        # Jira has the bad habit of returning errors in pages with 200 and
        # embedding the error in a huge webpage.
        if "<!-- SecurityTokenMissing -->" in content:
            self.log.warning("Got SecurityTokenMissing")
            raise JIRAError(f"SecurityTokenMissing: {content}")
            return False
        return True

    def _get_sprint_field_id(self):
        sprint_field_name = "Sprint"
        sprint_field_id = [
            f["schema"]["customId"]
            for f in self.fields()
            if f["name"] == sprint_field_name
        ][0]
        return sprint_field_id

    def _fetch_pages(
        self,
        item_type: Type[ResourceType],
        items_key: Optional[str],
        request_path: str,
        startAt: int = 0,
        maxResults: int = 50,
        params: Dict[str, Any] = None,
        base: str = JIRA_BASE_URL,
    ) -> ResultList[ResourceType]:
        """Fetch from a paginated end point.

        Args:
            item_type (Type[Resource]): Type of single item. ResultList of such items will be returned.
            items_key (Optional[str]): Path to the items in JSON returned from server.
              Set it to None, if response is an array, and not a JSON object.
            request_path (str): path in request URL
            startAt (int): index of the first record to be fetched. (Default: 0)
            maxResults (int): Maximum number of items to return.
              If maxResults evaluates as False, it will try to get all items in batches. (Default:50)
            params (Dict[str, Any]): Params to be used in all requests. Should not contain startAt and maxResults,
              as they will be added for each request created from this function.
            base (str): base URL to use for the requests.

        Returns:
            ResultList
        """
        async_workers = None
        async_class = None
        if self._options["async"]:
            try:
                from requests_futures.sessions import FuturesSession

                async_class = FuturesSession
            except ImportError:
                pass
            async_workers = self._options.get("async_workers")
        page_params = params.copy() if params else {}
        if startAt:
            page_params["startAt"] = startAt
        if maxResults:
            page_params["maxResults"] = maxResults

        resource = self._get_json(request_path, params=page_params, base=base)
        next_items_page = self._get_items_from_page(item_type, items_key, resource)
        items = next_items_page

        if True:  # isinstance(resource, dict):

            if isinstance(resource, dict):
                total = resource.get("total")
                total = int(total) if total is not None else total
                # 'isLast' is the optional key added to responses in Jira Agile 6.7.6. So far not used in basic Jira API.
                is_last = resource.get("isLast", False)
                start_at_from_response = resource.get("startAt", 0)
                max_results_from_response = resource.get("maxResults", 1)
            else:
                # if is a list
                total = 1
                is_last = True
                start_at_from_response = 0
                max_results_from_response = 1

            # If maxResults evaluates as False, get all items in batches
            if not maxResults:
                page_size = max_results_from_response or len(items)
                page_start = (startAt or start_at_from_response or 0) + page_size
                if (
                    async_class is not None
                    and not is_last
                    and (total is not None and len(items) < total)
                ):
                    async_fetches = []
                    future_session = async_class(
                        session=self._session, max_workers=async_workers
                    )
                    for start_index in range(page_start, total, page_size):
                        page_params = params.copy() if params else {}
                        page_params["startAt"] = start_index
                        page_params["maxResults"] = page_size
                        url = self._get_url(request_path)
                        r = future_session.get(url, params=page_params)
                        async_fetches.append(r)
                    for future in async_fetches:
                        response = future.result()
                        resource = json_loads(response)
                        if resource:
                            next_items_page = self._get_items_from_page(
                                item_type, items_key, resource
                            )
                            items.extend(next_items_page)
                while (
                    async_class is None
                    and not is_last
                    and (total is None or page_start < total)
                    and len(next_items_page) == page_size
                ):
                    page_params["startAt"] = page_start
                    page_params["maxResults"] = page_size
                    resource = self._get_json(
                        request_path, params=page_params, base=base
                    )
                    if resource:
                        next_items_page = self._get_items_from_page(
                            item_type, items_key, resource
                        )
                        items.extend(next_items_page)
                        page_start += page_size
                    else:
                        # if resource is an empty dictionary we assume no-results
                        break

            return ResultList(
                items, start_at_from_response, max_results_from_response, total, is_last
            )
        else:  # TODO: unreachable
            # it seems that search_users can return a list() containing a single user!
            return ResultList(
                [item_type(self._options, self._session, resource)], 0, 1, 1, True
            )

    def _get_items_from_page(
        self,
        item_type: Type[ResourceType],
        items_key: Optional[str],
        resource: Dict[str, Any],
    ) -> List[ResourceType]:
        try:
            return [
                # We need to ignore the type here, as 'Resource' is an option
                item_type(self._options, self._session, raw_issue_json)  # type: ignore
                for raw_issue_json in (resource[items_key] if items_key else resource)
            ]
        except KeyError as e:
            # improving the error text so we know why it happened
            raise KeyError(str(e) + " : " + json.dumps(resource))

    # Information about this client

    def client_info(self) -> str:
        """Get the server this client is connected to."""
        return self.server_url

    # Universal resource loading

    def find(
        self, resource_format: str, ids: Union[Tuple[str, str], int, str] = ""
    ) -> Resource:
        """Find Resource object for any addressable resource on the server.

        This method is a universal resource locator for any REST-ful resource in Jira. The
        argument ``resource_format`` is a string of the form ``resource``, ``resource/{0}``,
        ``resource/{0}/sub``, ``resource/{0}/sub/{1}``, etc. The format placeholders will be
        populated from the ``ids`` argument if present. The existing authentication session
        will be used.

        The return value is an untyped Resource object, which will not support specialized
        :py:meth:`.Resource.update` or :py:meth:`.Resource.delete` behavior. Moreover, it will
        not know to return an issue Resource if the client uses the resource issue path. For this
        reason, it is intended to support resources that are not included in the standard
        Atlassian REST API.

        Args:
            resource_format (str): the subpath to the resource string
            ids (Optional[Tuple]): values to substitute in the ``resource_format`` string
        Returns:
            Resource
        """
        resource = Resource(resource_format, self._options, self._session)
        resource.find(ids)
        return resource

    @no_type_check  # FIXME: This function fails type checking, probably a bug or two
    def async_do(self, size: int = 10):
        """Execute all asynchronous jobs and wait for them to finish. By default it will run on 10 threads.

        Args:
            size (int): number of threads to run on.
        """
        if hasattr(self._session, "_async_jobs"):
            self.log.info(
                "Executing asynchronous %s jobs found in queue by using %s threads..."
                % (len(self._session._async_jobs), size)
            )
            threaded_requests.map(self._session._async_jobs, size=size)

            # Application properties

    # non-resource
    def application_properties(
        self, key: str = None
    ) -> Union[Dict[str, str], List[Dict[str, str]]]:
        """Return the mutable server application properties.

        Args:
            key (Optional[str]): the single property to return a value for
        Returns:
            Union[Dict[str, str], List[Dict[str, str]]]
        """
        params = {}
        if key is not None:
            params["key"] = key
        return self._get_json("application-properties", params=params)

    def set_application_property(self, key: str, value: str):
        """Set the application property.

        Args:
            key (str): key of the property to set
            value (str): value to assign to the property
        """
        url = self._get_latest_url("application-properties/" + key)
        payload = {"id": key, "value": value}
        return self._session.put(url, data=json.dumps(payload))

    def applicationlinks(self, cached: bool = True) -> List:
        """List of application links.

        Returns:
            List[Dict]: json, or empty list
        """
        self._applicationlinks: List[Dict]  # for mypy benefit
        # if cached, return the last result
        if cached and hasattr(self, "_applicationlinks"):
            return self._applicationlinks

        # url = self._options['server'] + '/rest/applinks/latest/applicationlink'
        url = self.server_url + "/rest/applinks/latest/listApplicationlinks"

        r = self._session.get(url)

        o = json_loads(r)
        if "list" in o and isinstance(o, dict):
            self._applicationlinks = o["list"]
        else:
            self._applicationlinks = []
        return self._applicationlinks

    # Attachments
    def attachment(self, id: str) -> Attachment:
        """Get an attachment Resource from the server for the specified ID.

        Args:
            id (str): The Attachment ID

        Returns:
            Attachment
        """
        return self._find_for_resource(Attachment, id)

    # non-resource
    def attachment_meta(self) -> Dict[str, int]:
        """Get the attachment metadata.

        Return:
            Dict[str, int]
        """
        return self._get_json("attachment/meta")

    @translate_resource_args
    def add_attachment(
        self, issue: str, attachment: Union[str, BufferedReader], filename: str = None
    ) -> Attachment:
        """Attach an attachment to an issue and returns a Resource for it.

        The client will *not* attempt to open or validate the attachment; it expects a file-like object to be ready
        for its use. The user is still responsible for tidying up (e.g., closing the file, killing the socket, etc.)

        Args:
            issue (str): the issue to attach the attachment to
            attachment (Union[str,BufferedReader]): file-like object to attach to the issue, also works if it is a string with the filename.
            filename (str): optional name for the attached file. If omitted, the file object's ``name`` attribute
              is used. If you acquired the file-like object by any other method than ``open()``, make sure
              that a name is specified in one way or the other.

        Returns:
            Attachment
        """
        close_attachment = False
        if isinstance(attachment, str):
            attachment: BufferedReader = open(attachment, "rb")  # type: ignore
            attachment = cast(BufferedReader, attachment)
            close_attachment = True
        elif isinstance(attachment, BufferedReader) and attachment.mode != "rb":
            self.log.warning(
                "%s was not opened in 'rb' mode, attaching file may fail."
                % attachment.name
            )

        url = self._get_url("issue/" + str(issue) + "/attachments")

        fname = filename
        if not fname and isinstance(attachment, BufferedReader):
            fname = os.path.basename(attachment.name)

        if "MultipartEncoder" not in globals():
            method = "old"
            try:
                r = self._session.post(
                    url,
                    files={"file": (fname, attachment, "application/octet-stream")},
                    headers=CaseInsensitiveDict(
                        {"content-type": None, "X-Atlassian-Token": "no-check"}
                    ),
                )
            finally:
                if close_attachment:
                    attachment.close()
        else:
            method = "MultipartEncoder"

            def file_stream() -> MultipartEncoder:
                """Returns files stream of attachment."""
                return MultipartEncoder(
                    fields={"file": (fname, attachment, "application/octet-stream")}
                )

            m = file_stream()
            try:
                r = self._session.post(
                    url,
                    data=m,
                    headers=CaseInsensitiveDict(
                        {
                            "content-type": m.content_type,
                            "X-Atlassian-Token": "no-check",
                        }
                    ),
                    retry_data=file_stream,
                )
            finally:
                if close_attachment:
                    attachment.close()

        js: Union[Dict[str, Any], List[Dict[str, Any]]] = json_loads(r)
        if not js or not isinstance(js, Iterable):
            raise JIRAError(f"Unable to parse JSON: {js}")
        jira_attachment = Attachment(
            self._options, self._session, js[0] if isinstance(js, List) else js
        )
        if jira_attachment.size == 0:
            raise JIRAError(
                "Added empty attachment via %s method?!: r: %s\nattachment: %s"
                % (method, r, jira_attachment)
            )
        return jira_attachment

    def delete_attachment(self, id: str) -> Response:
        """Delete attachment by id.

        Args:
            id (str): ID of the attachment to delete

        Returns:
            Response
        """
        url = self._get_url("attachment/" + str(id))
        return self._session.delete(url)

    # Components

    def component(self, id: str):
        """Get a component Resource from the server.

        Args:
            id (str): ID of the component to get
        """
        return self._find_for_resource(Component, id)

    @translate_resource_args
    def create_component(
        self,
        name: str,
        project: str,
        description=None,
        leadUserName=None,
        assigneeType=None,
        isAssigneeTypeValid=False,
    ) -> Component:
        """Create a component inside a project and return a Resource for it.

        Args:
            name (str): name of the component
            project (str): key of the project to create the component in
            description (str): a description of the component
            leadUserName (Optional[str]): the username of the user responsible for this component
            assigneeType (Optional[str]): see the ComponentBean.AssigneeType class for valid values
            isAssigneeTypeValid (bool): boolean specifying whether the assignee type is acceptable (Default: False)

        Returns:
            Component
        """
        data = {
            "name": name,
            "project": project,
            "isAssigneeTypeValid": isAssigneeTypeValid,
        }
        if description is not None:
            data["description"] = description
        if leadUserName is not None:
            data["leadUserName"] = leadUserName
        if assigneeType is not None:
            data["assigneeType"] = assigneeType

        url = self._get_url("component")
        r = self._session.post(url, data=json.dumps(data))

        component = Component(self._options, self._session, raw=json_loads(r))
        return component

    def component_count_related_issues(self, id: str):
        """Get the count of related issues for a component.

        Args:
            id (str): ID of the component to use
        """
        data: Dict[str, Any] = self._get_json(
            "component/" + str(id) + "/relatedIssueCounts"
        )
        return data["issueCount"]

    def delete_component(self, id: str) -> Response:
        """Delete component by id.

        Args:
            id (str): ID of the component to use

        Returns:
            Response
        """
        url = self._get_url("component/" + str(id))
        return self._session.delete(url)

    # Custom field options

    def custom_field_option(self, id: str) -> CustomFieldOption:
        """Get a custom field option Resource from the server.

        Args:
            id (str): ID of the custom field to use

        Returns:
            CustomFieldOption
        """
        return self._find_for_resource(CustomFieldOption, id)

    # Dashboards

    def dashboards(
        self, filter=None, startAt=0, maxResults=20
    ) -> ResultList[Dashboard]:
        """Return a ResultList of Dashboard resources and a ``total`` count.

        Args:
            filter (Optional[str]): either "favourite" or "my", the type of dashboards to return
            startAt (int): index of the first dashboard to return (Default: 0)
            maxResults (int): maximum number of dashboards to return. If maxResults evaluates as False, it will try to get all items in batches. (Default: 20)

        Returns:
            ResultList
        """
        params = {}
        if filter is not None:
            params["filter"] = filter
        return self._fetch_pages(
            Dashboard, "dashboards", "dashboard", startAt, maxResults, params
        )

    def dashboard(self, id: str) -> Dashboard:
        """Get a dashboard Resource from the server.

        Args:
            id (str): ID of the dashboard to get.

        Returns:
            Dashboard
        """
        return self._find_for_resource(Dashboard, id)

    # Fields

    # non-resource
    def fields(self) -> List[Dict[str, Any]]:
        """Return a list of all issue fields.

        Returns:
            List[Dict[str, Any]]
        """
        return self._get_json("field")

    # Filters

    def filter(self, id: str) -> Filter:
        """Get a filter Resource from the server.

        Args:
            id (str): ID of the filter to get.

        Returns:
            Filter
        """
        return self._find_for_resource(Filter, id)

    def favourite_filters(self) -> List[Filter]:
        """Get a list of filter Resources which are the favourites of the currently authenticated user.

        Returns:
            List[Filter]
        """
        r_json: List[Dict[str, Any]] = self._get_json("filter/favourite")
        filters = [
            Filter(self._options, self._session, raw_filter_json)
            for raw_filter_json in r_json
        ]
        return filters

    def create_filter(
        self,
        name: str = None,
        description: str = None,
        jql: str = None,
        favourite: bool = None,
    ):
        """Create a new filter and return a filter Resource for it.

        Args:
            name (str): name of the new filter
            description (str): useful human readable description of the new filter
            jql (str): query string that defines the filter
            favourite (bool): whether to add this filter to the current user's favorites

        Returns:
            Filter

        """
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if jql is not None:
            data["jql"] = jql
        if favourite is not None:
            data["favourite"] = favourite
        url = self._get_url("filter")
        r = self._session.post(url, data=json.dumps(data))

        raw_filter_json: Dict[str, Any] = json_loads(r)
        return Filter(self._options, self._session, raw=raw_filter_json)

    def update_filter(
        self,
        filter_id,
        name: str = None,
        description: str = None,
        jql: str = None,
        favourite: bool = None,
    ):
        """Update a filter and return a filter Resource for it.

        Args:
            name (Optional[str]): name of the new filter
            description (Optional[str]): useful human readable description of the new filter
            jql (Optional[str]): query string that defines the filter
            favourite (Optional[bool]): whether to add this filter to the current user's favorites

        """
        filter = self.filter(filter_id)
        data = {}
        data["name"] = name or filter.name
        data["description"] = description or filter.description
        data["jql"] = jql or filter.jql
        data["favourite"] = favourite or filter.favourite

        url = self._get_url(f"filter/{filter_id}")
        r = self._session.put(
            url, headers={"content-type": "application/json"}, data=json.dumps(data)
        )

        raw_filter_json = json.loads(r.text)
        return Filter(self._options, self._session, raw=raw_filter_json)

    # Groups

    def group(self, id: str, expand: Any = None) -> Group:
        """Get a group Resource from the server.

        Args:
            id (str): ID of the group to get
            expand (Optional[Any]): Extra information to fetch inside each resource

        Returns:
            Group
        """
        group = Group(self._options, self._session)
        params = {}
        if expand is not None:
            params["expand"] = expand
        group.find(id, params=params)
        return group

    # non-resource
    def groups(
        self,
        query: Optional[str] = None,
        exclude: Optional[Any] = None,
        maxResults: int = 9999,
    ) -> List[str]:
        """Return a list of groups matching the specified criteria.

        Args:
            query (Optional[str]): filter groups by name with this string
            exclude (Optional[Any]): filter out groups by name with this string
            maxResults (int): maximum results to return. (Default: 9999)
        Returns:
            List[str]

        """
        params: Dict[str, Any] = {}
        groups = []
        if query is not None:
            params["query"] = query
        if exclude is not None:
            params["exclude"] = exclude
        if maxResults is not None:
            params["maxResults"] = maxResults
        for group in self._get_json("groups/picker", params=params)["groups"]:
            groups.append(group["name"])
        return sorted(groups)

    def group_members(self, group: str) -> OrderedDict:
        """Return a hash or users with their information. Requires Jira 6.0 or will raise NotImplemented.

        Args:
            group (str): Name of the group.
        """
        if self._version < (6, 0, 0):
            raise NotImplementedError(
                "Group members is not implemented in Jira before version 6.0, upgrade the instance, if possible."
            )

        params = {"groupname": group, "expand": "users"}
        r = self._get_json("group", params=params)
        size = r["users"]["size"]
        end_index = r["users"]["end-index"]

        while end_index < size - 1:
            params = {
                "groupname": group,
                "expand": f"users[{end_index + 1}:{end_index + 50}]",
            }
            r2 = self._get_json("group", params=params)
            for user in r2["users"]["items"]:
                r["users"]["items"].append(user)
            end_index = r2["users"]["end-index"]
            size = r["users"]["size"]

        result = {}
        for user in r["users"]["items"]:
            # 'id' is likely available only in older JIRA Server, it's not available on newer JIRA Server.
            # 'name' is not available in JIRA Cloud.
            hasId = user.get("id") is not None and user.get("id") != ""
            hasName = user.get("name") is not None and user.get("name") != ""
            result[
                user["id"]
                if hasId
                else user.get("name")
                if hasName
                else user.get("accountId")
            ] = {
                "name": user.get("name"),
                "id": user.get("id"),
                "accountId": user.get("accountId"),
                "fullname": user.get("displayName"),
                "email": user.get("emailAddress", "hidden"),
                "active": user.get("active"),
                "timezone": user.get("timezone"),
            }
        return OrderedDict(sorted(result.items(), key=lambda t: t[0]))

    def add_group(self, groupname: str) -> bool:
        """Create a new group in Jira.

        Args:
            groupname (str): The name of the group you wish to create.

        Returns:
            bool: True if successful.
        """
        url = self._get_latest_url("group")

        # implementation based on
        # https://docs.atlassian.com/jira/REST/ondemand/#d2e5173

        x = OrderedDict()

        x["name"] = groupname

        payload = json.dumps(x)

        self._session.post(url, data=payload)

        return True

    def remove_group(self, groupname: str) -> bool:
        """Delete a group from the Jira instance.

        Args:
            groupname (str): The group to be deleted from the Jira instance.

        Returns:
            bool: Returns True on success.
        """
        # implementation based on
        # https://docs.atlassian.com/jira/REST/ondemand/#d2e5173
        url = self._get_latest_url("group")
        x = {"groupname": groupname}
        self._session.delete(url, params=x)
        return True

    # Issues

    def issue(
        self,
        id: Union[Issue, str],
        fields: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> Issue:
        """Get an issue Resource from the server.

        Args:
            id (Union[Issue, str]): ID or key of the issue to get
            fields (Optional[str]): comma-separated string of issue fields to include in the results
            expand (Optional[str]): extra information to fetch inside each resource
        Returns:
            Issue
        """
        # this allows us to pass Issue objects to issue()
        if isinstance(id, Issue):
            return id

        issue = Issue(self._options, self._session)

        params = {}
        if fields is not None:
            params["fields"] = fields
        if expand is not None:
            params["expand"] = expand
        issue.find(id, params=params)
        return issue

    def create_issue(
        self,
        fields: Optional[Dict[str, Any]] = None,
        prefetch: bool = True,
        **fieldargs,
    ) -> Issue:
        """Create a new issue and return an issue Resource for it.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored.

        By default, the client will immediately reload the issue Resource created by this method in order to return
        a complete Issue object to the caller; this behavior can be controlled through the 'prefetch' argument.

        Jira projects may contain many different issue types. Some issue screens have different requirements for
        fields in a new issue. This information is available through the 'createmeta' method. Further examples are
        available here: https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+Example+-+Create+Issue

        Args:
            fields (Optional[Dict[str, Any]]): a dict containing field names and the values to use. If present, all other keyword arguments
              will be ignored
            prefetch (bool): whether to reload the created issue Resource so that all of its data is present in the value
              returned from this method
        Returns:
            Issue
        """
        data: Dict[str, Any] = _field_worker(fields, **fieldargs)

        p = data["fields"]["project"]

        if isinstance(p, str) or isinstance(p, int):
            data["fields"]["project"] = {"id": self.project(str(p)).id}

        p = data["fields"]["issuetype"]
        if isinstance(p, int):
            data["fields"]["issuetype"] = {"id": p}
        if isinstance(p, str) or isinstance(p, int):
            data["fields"]["issuetype"] = {"id": self.issue_type_by_name(str(p)).id}

        url = self._get_url("issue")
        r = self._session.post(url, data=json.dumps(data))

        raw_issue_json = json_loads(r)
        if "key" not in raw_issue_json:
            raise JIRAError(
                status_code=r.status_code, response=r, url=url, text=json.dumps(data)
            )
        if prefetch:
            return self.issue(raw_issue_json["key"])
        else:
            return Issue(self._options, self._session, raw=raw_issue_json)

    def create_issues(
        self, field_list: List[Dict[str, Any]], prefetch: bool = True
    ) -> List[Dict[str, Any]]:
        """Bulk create new issues and return an issue Resource for each successfully created issue.

        See `create_issue` documentation for field information.

        Args:
            field_list (List[Dict[str, Any]]): a list of dicts each containing field names and the values to use. Each dict
              is an individual issue to create and is subject to its minimum requirements.
            prefetch (bool): whether to reload the created issue Resource for each created issue so that all
              of its data is present in the value returned from this method.
        Returns:
            List[Dict[str, Any]]

        """
        data: Dict[str, List] = {"issueUpdates": []}
        for field_dict in field_list:
            issue_data: Dict[str, Any] = _field_worker(field_dict)
            p = issue_data["fields"]["project"]

            if isinstance(p, str) or isinstance(p, int):
                issue_data["fields"]["project"] = {"id": self.project(str(p)).id}

            p = issue_data["fields"]["issuetype"]
            if isinstance(p, int):
                issue_data["fields"]["issuetype"] = {"id": p}
            if isinstance(p, str):
                issue_data["fields"]["issuetype"] = {
                    "id": self.issue_type_by_name(str(p)).id
                }

            data["issueUpdates"].append(issue_data)

        url = self._get_url("issue/bulk")
        try:
            r = self._session.post(url, data=json.dumps(data))
            raw_issue_json = json_loads(r)
        # Catching case where none of the issues has been created. See https://github.com/pycontribs/jira/issues/350
        except JIRAError as je:
            if je.status_code == 400 and je.response:
                raw_issue_json = json.loads(je.response.text)
            else:
                raise
        issue_list = []
        errors = {}
        for error in raw_issue_json["errors"]:
            errors[error["failedElementNumber"]] = error["elementErrors"]["errors"]
        for index, fields in enumerate(field_list):
            if index in errors:
                issue_list.append(
                    {
                        "status": "Error",
                        "error": errors[index],
                        "issue": None,
                        "input_fields": fields,
                    }
                )
            else:
                issue = raw_issue_json["issues"].pop(0)
                if prefetch:
                    issue = self.issue(issue["key"])
                else:
                    issue = Issue(self._options, self._session, raw=issue)
                issue_list.append(
                    {
                        "status": "Success",
                        "issue": issue,
                        "error": None,
                        "input_fields": fields,
                    }
                )
        return issue_list

    def supports_service_desk(self):
        """Returns whether or not the Jira instance supports service desk.

        Returns:
            bool
        """
        url = self.server_url + "/rest/servicedeskapi/info"
        headers = {"X-ExperimentalApi": "opt-in"}
        try:
            r = self._session.get(url, headers=headers)
            return r.status_code == 200
        except JIRAError:
            return False

    def create_customer(self, email: str, displayName: str) -> Customer:
        """Create a new customer and return an issue Resource for it.

        Args:
            email (str): Customer Email
            displayName (str): Customer display name
        Returns:
            Customer

        """
        url = self.server_url + "/rest/servicedeskapi/customer"
        headers = {"X-ExperimentalApi": "opt-in"}
        r = self._session.post(
            url,
            headers=headers,
            data=json.dumps({"email": email, "displayName": displayName}),
        )

        raw_customer_json = json_loads(r)

        if r.status_code != 201:
            raise JIRAError(status_code=r.status_code, request=r)
        return Customer(self._options, self._session, raw=raw_customer_json)

    def service_desks(self) -> List[ServiceDesk]:
        """Get a list of ServiceDesk Resources from the server visible to the current authenticated user.

        Returns:
            List[ServiceDesk]

        """
        url = self.server_url + "/rest/servicedeskapi/servicedesk"
        headers = {"X-ExperimentalApi": "opt-in"}
        r_json = json_loads(self._session.get(url, headers=headers))
        print(r_json)
        projects = [
            ServiceDesk(self._options, self._session, raw_project_json)
            for raw_project_json in r_json["values"]
        ]
        return projects

    def service_desk(self, id: str) -> ServiceDesk:
        """Get a Service Desk Resource from the server.

        Args:
            id (str): ID or key of the Service Desk to get

        Returns:
            ServiceDesk

        """
        return self._find_for_resource(ServiceDesk, id)

    @no_type_check  # FIXME: This function does not do what it wants to with fieldargs
    def create_customer_request(
        self, fields: Dict[str, Any] = None, prefetch: bool = True, **fieldargs
    ) -> Issue:
        """Create a new customer request and return an issue Resource for it.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored.

        By default, the client will immediately reload the issue Resource created by this method in order to return
        a complete Issue object to the caller; this behavior can be controlled through the 'prefetch' argument.

        Jira projects may contain many different issue types. Some issue screens have different requirements for
        fields in a new issue. This information is available through the 'createmeta' method. Further examples are
        available here: https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+Example+-+Create+Issue

        Args:
            fields (Dict[str, Any]): a dict containing field names and the values to use. If present, all other keyword arguments
              will be ignored
            prefetch (bool): whether to reload the created issue Resource so that all of its data is present in the value
              returned from this method
        Returns:
            Issue
        """
        data = fields

        p = data["serviceDeskId"]
        service_desk = None

        if isinstance(p, str) or isinstance(p, int):
            service_desk = self.service_desk(p)
        elif isinstance(p, ServiceDesk):
            service_desk = p

        data["serviceDeskId"] = service_desk.id

        p = data["requestTypeId"]
        if isinstance(p, int):
            data["requestTypeId"] = p
        elif isinstance(p, str):
            data["requestTypeId"] = self.request_type_by_name(service_desk, p).id

        url = self.server_url + "/rest/servicedeskapi/request"
        headers = {"X-ExperimentalApi": "opt-in"}
        r = self._session.post(url, headers=headers, data=json.dumps(data))

        raw_issue_json = json_loads(r)
        if "issueKey" not in raw_issue_json:
            raise JIRAError(status_code=r.status_code, request=r)
        if prefetch:
            return self.issue(raw_issue_json["issueKey"])
        else:
            return Issue(self._options, self._session, raw=raw_issue_json)

    def createmeta(
        self,
        projectKeys: Optional[Union[Tuple[str, str], str]] = None,
        projectIds: Union[List, Tuple[str, str]] = [],
        issuetypeIds: Optional[List[str]] = None,
        issuetypeNames: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the metadata required to create issues, optionally filtered by projects and issue types.

        Args:
            projectKeys (Optional[Union[Tuple[str, str], str]]): keys of the projects to filter the results with.
              Can be a single value or a comma-delimited string. May be combined
              with projectIds.
            projectIds (Union[List, Tuple[str, str]]): IDs of the projects to filter the results with. Can
              be a single value or a comma-delimited string. May be combined with
              projectKeys.
            issuetypeIds (Optional[List[str]]): IDs of the issue types to filter the results with.
              Can be a single value or a comma-delimited string. May be combined
              with issuetypeNames.
            issuetypeNames (Optional[str]): Names of the issue types to filter the results
              with. Can be a single value or a comma-delimited string. May be
              combined with issuetypeIds.
            expand (Optional[str]): extra information to fetch inside each resource.
        Returns:
            Dict[str, Any]

        """
        params: Dict[str, Any] = {}
        if projectKeys is not None:
            params["projectKeys"] = projectKeys
        if projectIds is not None:
            if isinstance(projectIds, str):
                projectIds = projectIds.split(",")
            params["projectIds"] = projectIds
        if issuetypeIds is not None:
            params["issuetypeIds"] = issuetypeIds
        if issuetypeNames is not None:
            params["issuetypeNames"] = issuetypeNames
        if expand is not None:
            params["expand"] = expand
        return self._get_json("issue/createmeta", params)

    def _get_user_identifier(self, user: User) -> str:
        """Get the unique identifier depending on the deployment type.

        - Cloud: 'accountId'
        - Self Hosted: 'name' (equivalent to username)

        Args:
            user (User): a User object

        Returns:
            str: the User's unique identifier.
        """
        return user.accountId if self._is_cloud else user.name

    def _get_user_id(self, user: str) -> str:
        """Internal method for translating an user search (str) to an id.

        This function uses :py:meth:`JIRA.search_users` to find the user
        and then using :py:meth:`JIRA._get_user_identifier` extracts
        the relevant identifier property depending on whether
        the instance is a Cloud or self-hosted Instance.


        Args:
            user (str): The search term used for finding a user.

        Raises:
            JIRAError: If any error occurs.

        Returns:
            str: The Jira user's identifier.
        """
        try:
            user_obj: User
            if self._is_cloud:
                user_obj = self.search_users(query=user, maxResults=1)[0]
            else:
                user_obj = self.search_users(user=user, maxResults=1)[0]
        except Exception as e:
            raise JIRAError(str(e))
        return self._get_user_identifier(user_obj)

    # non-resource
    @translate_resource_args
    def assign_issue(self, issue: Union[int, str], assignee: str) -> bool:
        """Assign an issue to a user. None will set it to unassigned. -1 will set it to Automatic.

        Args:
            issue (Union[int,str]): the issue ID or key to assign
            assignee (str): the user to assign the issue to

        Returns:
            bool
        """
        url = self._get_latest_url("issue/{}/assignee".format(str(issue)))
        user_id = self._get_user_id(assignee)
        payload = {"accountId": user_id} if self._is_cloud else {"name": user_id}
        r = self._session.put(url, data=json.dumps(payload))
        raise_on_error(r)
        return True

    @translate_resource_args
    def comments(self, issue: str, expand: Optional[str] = None) -> List[Comment]:
        """Get a list of comment Resources.

        :param issue: the issue to get comments from
        :type issue: str
        :param expand: extra information to fetch for each comment
                       such as renderedBody and properties.
        :type expand: str
        :rtype: List[Comment]
        """
        params = {}
        if expand is not None:
            params["expand"] = expand
        r_json = self._get_json("issue/{}/comment".format(str(issue)), params=params)

        comments = [
            Comment(self._options, self._session, raw_comment_json)
            for raw_comment_json in r_json["comments"]
        ]
        return comments

    @translate_resource_args
    def comment(
        self, issue: str, comment: str, expand: Optional[str] = None
    ) -> Comment:
        """Get a comment Resource from the server for the specified ID.

        :param issue: ID or key of the issue to get the comment from
        :param comment: ID of the comment to get
        :param expand: extra information to fetch for comment
                       such as renderedBody and properties.
        """
        return self._find_for_resource(Comment, (issue, comment), expand=expand)

    @translate_resource_args
    def add_comment(
        self,
        issue: str,
        body: str,
        visibility: Optional[Dict[str, str]] = None,
        is_internal: bool = False,
    ) -> Comment:
        """Add a comment from the current authenticated user on the specified issue and return a Resource for it.

        The issue identifier and comment body are required.

        Args:
            issue (str): ID or key of the issue to add the comment to
            body (str): Text of the comment to add
            visibility (Optional[Dict[str, str]]): a dict containing two entries: "type" and "value".
              "type" is 'role' (or 'group' if the Jira server has configured
              comment visibility for groups) and 'value' is the name of the role
              (or group) to which viewing of this comment will be restricted.
            is_internal (bool): Defines whether a comment has to be marked as 'Internal' in Jira Service Desk (Default: False)

        Returns:
            Comment: the created comment

        """
        data: Dict[str, Any] = {"body": body}

        if is_internal:
            data.update(
                {
                    "properties": [
                        {"key": "sd.public.comment", "value": {"internal": is_internal}}
                    ]
                }
            )

        if visibility is not None:
            data["visibility"] = visibility

        url = self._get_url("issue/" + str(issue) + "/comment")
        r = self._session.post(url, data=json.dumps(data))

        comment = Comment(self._options, self._session, raw=json_loads(r))
        return comment

    # non-resource
    @translate_resource_args
    def editmeta(self, issue: Union[str, int]):
        """Get the edit metadata for an issue.

        Args:
            issue (str): the issue to get metadata for

        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]

        """
        return self._get_json("issue/" + str(issue) + "/editmeta")

    @translate_resource_args
    def remote_links(self, issue: Union[str, int]) -> List[RemoteLink]:
        """Get a list of remote link Resources from an issue.

        Args:
            issue (str): the issue to get remote links from
        """
        r_json = self._get_json("issue/" + str(issue) + "/remotelink")
        remote_links = [
            RemoteLink(self._options, self._session, raw_remotelink_json)
            for raw_remotelink_json in r_json
        ]
        return remote_links

    @translate_resource_args
    def remote_link(self, issue: str, id: str) -> RemoteLink:
        """Get a remote link Resource from the server.

        Args:
            issue (str): the issue holding the remote link
            id (str): ID of the remote link
        """
        return self._find_for_resource(RemoteLink, (issue, id))

    # removed the @translate_resource_args because it prevents us from finding
    # information for building a proper link
    def add_remote_link(
        self,
        issue: str,
        destination: Union[Issue, Dict[str, Any]],
        globalId: Optional[str] = None,
        application: Optional[Dict[str, Any]] = None,
        relationship: Optional[str] = None,
    ) -> RemoteLink:
        """Add a remote link from an issue to an external application and returns a remote link Resource for it.

        ``destination`` should be a dict containing at least ``url`` to the linked external URL and
        ``title`` to display for the link inside Jira.

        For definitions of the allowable fields for ``destination`` and the keyword arguments ``globalId``, ``application``
        and ``relationship``, see https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+for+Remote+Issue+Links.

        Args:
            issue (str): the issue to add the remote link to
            destination (Union[Issue, Dict[str, Any]]): the link details to add (see the above link for details)
            globalId (Optional[str]): unique ID for the link (see the above link for details)
            application (Optional[Dict[str,Any]]): application information for the link (see the above link for details)
            relationship (Optional[str]): relationship description for the link (see the above link for details)

        Returns:
            RemoteLink: the added remote lint
        """
        try:
            applicationlinks: List[Dict] = self.applicationlinks()
        except JIRAError as e:
            applicationlinks = []
            # In many (if not most) configurations, non-admin users are
            # not allowed to list applicationlinks; if we aren't allowed,
            # let's let people try to add remote links anyway, we just
            # won't be able to be quite as helpful.
            warnings.warn(
                "Unable to gather applicationlinks; you will not be able "
                "to add links to remote issues: (%s) %s" % (e.status_code, e.text),
                Warning,
            )

        data: Dict[str, Any] = {}
        if isinstance(destination, Issue) and destination.raw:
            data["object"] = {"title": str(destination), "url": destination.permalink()}
            for x in applicationlinks:
                if x["application"]["displayUrl"] == destination._options["server"]:
                    data["globalId"] = "appId=%s&issueId=%s" % (
                        x["application"]["id"],
                        destination.raw["id"],
                    )
                    data["application"] = {
                        "name": x["application"]["name"],
                        "type": "com.atlassian.jira",
                    }
                    break
            if "globalId" not in data:
                raise NotImplementedError("Unable to identify the issue to link to.")
        else:

            if globalId is not None:
                data["globalId"] = globalId
            if application is not None:
                data["application"] = application
            data["object"] = destination

        if relationship is not None:
            data["relationship"] = relationship

        # check if the link comes from one of the configured application links
        if isinstance(destination, Issue) and destination.raw:
            for x in applicationlinks:
                if x["application"]["displayUrl"] == self.server_url:
                    data["globalId"] = "appId=%s&issueId=%s" % (
                        x["application"]["id"],
                        destination.raw["id"],  # .raw only present on Issue
                    )
                    data["application"] = {
                        "name": x["application"]["name"],
                        "type": "com.atlassian.jira",
                    }
                    break

        url = self._get_url("issue/" + str(issue) + "/remotelink")
        r = self._session.post(url, data=json.dumps(data))

        remote_link = RemoteLink(self._options, self._session, raw=json_loads(r))
        return remote_link

    def add_simple_link(self, issue: str, object: Dict[str, Any]):
        """Add a simple remote link from an issue to web resource.

        This avoids the admin access problems from add_remote_link by just
        using a simple object and presuming all fields are correct and not
        requiring more complex ``application`` data.

        ``object`` should be a dict containing at least ``url`` to the
        linked external URL and ``title`` to display for the link inside Jira.

        For definitions of the allowable fields for ``object`` , see https://developer.atlassian.com/display/JIRADEV/JIRA+REST+API+for+Remote+Issue+Links.

        Args:
            issue (str): the issue to add the remote link to
            object (Dict[str,Any]): the dictionary used to create remotelink data

        Returns:
            RemoteLint
        """
        data = {"object": object}
        url = self._get_url("issue/" + str(issue) + "/remotelink")
        r = self._session.post(url, data=json.dumps(data))

        simple_link = RemoteLink(self._options, self._session, raw=json_loads(r))
        return simple_link

    # non-resource
    @translate_resource_args
    def transitions(self, issue: str, id: Optional[str] = None, expand=None):
        """Get a list of the transitions available on the specified issue to the current user.

        Args:
            issue (str): ID or key of the issue to get the transitions from
            id (Optional[str]): if present, get only the transition matching this ID
            expand (Optional): extra information to fetch inside each transition

        Returns:
            Any: json of response
        """
        params = {}
        if id is not None:
            params["transitionId"] = id
        if expand is not None:
            params["expand"] = expand
        return self._get_json("issue/" + str(issue) + "/transitions", params=params)[
            "transitions"
        ]

    def find_transitionid_by_name(
        self, issue: str, transition_name: str
    ) -> Optional[int]:
        """Get a transitionid available on the specified issue to the current user.

        Look at https://developer.atlassian.com/static/rest/jira/6.1.html#d2e1074 for json reference

        Args:
            issue (str): ID or key of the issue to get the transitions from
            trans_name (str): iname of transition we are looking for
        """
        transitions_json = self.transitions(issue)
        id: Optional[int] = None

        for transition in transitions_json:
            if transition["name"].lower() == transition_name.lower():
                id = transition["id"]
                break
        return id

    @translate_resource_args
    def transition_issue(
        self,
        issue: str,
        transition: str,
        fields: Optional[Dict[str, Any]] = None,
        comment: Optional[str] = None,
        worklog: Optional[str] = None,
        **fieldargs,
    ):
        """Perform a transition on an issue.

        Each keyword argument (other than the predefined ones) is treated as a field name and the argument's value
        is treated as the intended value for that field -- if the fields argument is used, all other keyword arguments
        will be ignored. Field values will be set on the issue as part of the transition process.

        Args:
            issue (str): ID or key of the issue to perform the transition on
            transition (str): ID or name of the transition to perform
            fields (Optional[Dict[str,Any]]): a dict containing field names and the values to use.
            comment (Optional[str]): String to add as comment to the issue when performing the transition.
            workload (Optional[str]): String to add as time spent on the issue when performing the transition.
            **fieldargs: If present, all other keyword arguments will be ignored
        """
        transitionId: Optional[int] = None

        try:
            transitionId = int(transition)
        except Exception:
            # cannot cast to int, so try to find transitionId by name
            transitionId = self.find_transitionid_by_name(issue, transition)
            if transitionId is None:
                raise JIRAError(f"Invalid transition name. {transition}")

        data: Dict[str, Any] = {"transition": {"id": transitionId}}
        if comment:
            data["update"] = {"comment": [{"add": {"body": comment}}]}
        if worklog:
            data["update"] = {"worklog": [{"add": {"timeSpent": worklog}}]}
        if fields is not None:
            data["fields"] = fields
        else:
            fields_dict = {}
            for field in fieldargs:
                fields_dict[field] = fieldargs[field]
            data["fields"] = fields_dict

        url = self._get_url("issue/" + str(issue) + "/transitions")
        r = self._session.post(url, data=json.dumps(data))
        try:
            r_json = json_loads(r)
        except ValueError as e:
            self.log.error(f"{e}\n{r.text}")
            raise e
        return r_json

    @translate_resource_args
    def votes(self, issue: str) -> Votes:
        """Get a votes Resource from the server.

        Args:
            issue (str): ID or key of the issue to get the votes for
        Returns:
            Votes
        """
        return self._find_for_resource(Votes, issue)

    @translate_resource_args
    def add_vote(self, issue: str) -> Response:
        """Register a vote for the current authenticated user on an issue.

        Args:
            issue (str): ID or key of the issue to vote on

        Returns:
            Response
        """
        url = self._get_url("issue/" + str(issue) + "/votes")
        return self._session.post(url)

    @translate_resource_args
    def remove_vote(self, issue: str):
        """Remove the current authenticated user's vote from an issue.

        Args:
            issue (str): ID or key of the issue to remove vote on
        """
        url = self._get_url("issue/" + str(issue) + "/votes")
        self._session.delete(url)

    @translate_resource_args
    def watchers(self, issue: str) -> Watchers:
        """Get a watchers Resource from the server for an issue.

        Args:
            issue (str): ID or key of the issue to get the watchers for
        Returns:
            Watchers
        """
        return self._find_for_resource(Watchers, issue)

    @translate_resource_args
    def add_watcher(self, issue: str, watcher: str) -> Response:
        """Add a user to an issue's watchers list.

        Args:
            issue (str): ID or key of the issue affected
            watcher (str): name of the user to add to the watchers list
        """
        url = self._get_url("issue/" + str(issue) + "/watchers")
        return self._session.post(url, data=json.dumps(watcher))

    @translate_resource_args
    def remove_watcher(self, issue: str, watcher: str) -> Response:
        """Remove a user from an issue's watch list.

        Args:
            issue (str): ID or key of the issue affected
            watcher (str): name of the user to remove from the watchers list

        Returns:
            Response
        """
        url = self._get_url("issue/" + str(issue) + "/watchers")
        # https://docs.atlassian.com/software/jira/docs/api/REST/8.13.6/#api/2/issue-removeWatcher
        user_id = self._get_user_id(watcher)
        payload = {"accountId": user_id} if self._is_cloud else {"username": user_id}
        result = self._session.delete(url, params=payload)
        return result

    @translate_resource_args
    def worklogs(self, issue: str) -> List[Worklog]:
        """Get a list of worklog Resources from the server for an issue.

        Args:
            issue (str): ID or key of the issue to get worklogs from
        Returns:
            List[Worklog]
        """
        r_json = self._get_json("issue/" + str(issue) + "/worklog")
        worklogs = [
            Worklog(self._options, self._session, raw_worklog_json)
            for raw_worklog_json in r_json["worklogs"]
        ]
        return worklogs

    @translate_resource_args
    def worklog(self, issue: str, id: str) -> Worklog:
        """Get a specific worklog Resource from the server.

        Args:
            issue (str): ID or key of the issue to get the worklog from
            id (str): ID of the worklog to get
        Returns:
            Worklog
        """
        return self._find_for_resource(Worklog, (issue, id))

    @translate_resource_args
    def add_worklog(
        self,
        issue,
        timeSpent: (Optional[str]) = None,
        timeSpentSeconds: (Optional[str]) = None,
        adjustEstimate: (Optional[str]) = None,
        newEstimate: (Optional[str]) = None,
        reduceBy: (Optional[str]) = None,
        comment: (Optional[str]) = None,
        started: (Optional[datetime.datetime]) = None,
        user: (Optional[str]) = None,
    ) -> Worklog:
        """Add a new worklog entry on an issue and return a Resource for it.

        Args:
            issue (str): the issue to add the worklog to
            timeSpent (Optional[str]): a worklog entry with this amount of time spent, e.g. "2d"
            timeSpentSeconds (Optional[str]): a worklog entry with this amount of time spent in seconds
            adjustEstimate (Optional[str]):  allows the user to provide specific instructions to update
              the remaining time estimate of the issue. The value can either be ``new``, ``leave``, ``manual`` or ``auto`` (default).
            newEstimate (Optional[str]): the new value for the remaining estimate field. e.g. "2d"
            reduceBy (Optional[str]): the amount to reduce the remaining estimate by e.g. "2d"
            comment (Optional[str]): optional worklog comment
            started (Optional[datetime.datetime]): Moment when the work is logged, if not specified will default to now
            user (Optional[str]): the user ID or name to use for this worklog
        Returns:
            Worklog
        """
        params = {}
        if adjustEstimate is not None:
            params["adjustEstimate"] = adjustEstimate
        if newEstimate is not None:
            params["newEstimate"] = newEstimate
        if reduceBy is not None:
            params["reduceBy"] = reduceBy

        data: Dict[str, Any] = {}
        if timeSpent is not None:
            data["timeSpent"] = timeSpent
        if timeSpentSeconds is not None:
            data["timeSpentSeconds"] = timeSpentSeconds
        if comment is not None:
            data["comment"] = comment
        elif user:
            # we log user inside comment as it doesn't always work
            data["comment"] = user

        if started is not None:
            # based on REST Browser it needs: "2014-06-03T08:21:01.273+0000"
            if started.tzinfo is None:
                data["started"] = started.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
            else:
                data["started"] = started.strftime("%Y-%m-%dT%H:%M:%S.000%z")
        if user is not None:
            data["author"] = {
                "name": user,
                "self": self.JIRA_BASE_URL + "/rest/api/latest/user?username=" + user,
                "displayName": user,
                "active": False,
            }
            data["updateAuthor"] = data["author"]
        # report bug to Atlassian: author and updateAuthor parameters are
        # ignored.
        url = self._get_url(f"issue/{issue}/worklog")
        r = self._session.post(url, params=params, data=json.dumps(data))

        return Worklog(self._options, self._session, json_loads(r))

    # Issue links

    @translate_resource_args
    def create_issue_link(
        self,
        type: Union[str, IssueLinkType],
        inwardIssue: str,
        outwardIssue: str,
        comment: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Create a link between two issues.

        Args:
            type (Union[str,IssueLinkType]): the type of link to create
            inwardIssue: the issue to link from
            outwardIssue: the issue to link to
            comment (Optional[Dict[str, Any]]):  a comment to add to the issues with the link.
              Should be a dict containing ``body`` and ``visibility`` fields: ``body`` being
              the text of the comment and ``visibility`` being a dict containing
              two entries: ``type`` and ``value``. ``type`` is ``role`` (or
              ``group`` if the Jira server has configured comment visibility for
              groups) and ``value`` is the name of the role (or group) to which
              viewing of this comment will be restricted.

        Returns:
            Response
        """
        # let's see if we have the right issue link 'type' and fix it if needed
        issue_link_types = self.issue_link_types()

        if type not in issue_link_types:
            for lt in issue_link_types:
                if lt.outward == type:
                    # we are smart to figure it out what he meant
                    type = lt.name
                    break
                elif lt.inward == type:
                    # so that's the reverse, so we fix the request
                    type = lt.name
                    inwardIssue, outwardIssue = outwardIssue, inwardIssue
                    break

        data = {
            "type": {"name": type},
            "inwardIssue": {"key": inwardIssue},
            "outwardIssue": {"key": outwardIssue},
            "comment": comment,
        }
        url = self._get_url("issueLink")
        return self._session.post(url, data=json.dumps(data))

    def delete_issue_link(self, id: str):
        """Delete a link between two issues.

        Args:
            id (str): ID of the issue link to delete
        """
        url = self._get_url("issueLink") + "/" + id
        return self._session.delete(url)

    def issue_link(self, id: str):
        """Get an issue link Resource from the server.

        Args:
            id (str): ID of the issue link to get
        """
        return self._find_for_resource(IssueLink, id)

    # Issue link types

    def issue_link_types(self, force: bool = False) -> List[IssueLinkType]:
        """Get a list of issue link type Resources from the server.

        Returns:
            List[IssueLinkType]
        """
        if not hasattr(self, "self._cached_issue_link_types") or force:
            r_json = self._get_json("issueLinkType")
            self._cached_issue_link_types = [
                IssueLinkType(self._options, self._session, raw_link_json)
                for raw_link_json in r_json["issueLinkTypes"]
            ]
        return self._cached_issue_link_types

    def issue_link_type(self, id: str) -> IssueLinkType:
        """Get an issue link type Resource from the server.

        Args:
            id (str): ID of the issue link type to get

        Returns:
            IssueLinkType

        """
        return self._find_for_resource(IssueLinkType, id)

    # Issue types

    def issue_types(self) -> List[IssueType]:
        """Get a list of issue type Resources from the server.

        Returns:
            List[IssueType]

        """
        r_json = self._get_json("issuetype")
        issue_types = [
            IssueType(self._options, self._session, raw_type_json)
            for raw_type_json in r_json
        ]
        return issue_types

    def issue_type(self, id: str) -> IssueType:
        """Get an issue type Resource from the server.

        Args:
            id (str): ID of the issue type to get

        Returns:
            IssueType
        """
        return self._find_for_resource(IssueType, id)

    def issue_type_by_name(self, name: str) -> IssueType:
        """
        Args:
            name (str): Name of the issue type

        Returns:
            IssueType
        """
        matching_issue_types = [it for it in self.issue_types() if it.name == name]
        if len(matching_issue_types) == 1:
            return matching_issue_types[0]
        elif len(matching_issue_types) == 0:
            raise KeyError(f"Issue type '{name}' is unknown.")
        else:
            raise KeyError(f"Issue type '{name}' appears more than once.")

    def request_types(self, service_desk: ServiceDesk) -> List[RequestType]:
        """Returns request types supported by a service desk instance.

        Args:
            service_desk (ServiceDesk): The service desk instance.

        Returns:
            List[RequestType]
        """
        if hasattr(service_desk, "id"):
            service_desk = service_desk.id
        url = (
            self.server_url
            + f"/rest/servicedeskapi/servicedesk/{service_desk}/requesttype"
        )
        headers = {"X-ExperimentalApi": "opt-in"}
        r_json = json_loads(self._session.get(url, headers=headers))
        request_types = [
            RequestType(self._options, self._session, raw_type_json)
            for raw_type_json in r_json["values"]
        ]
        return request_types

    def request_type_by_name(self, service_desk: ServiceDesk, name: str):
        request_types = self.request_types(service_desk)
        try:
            request_type = [rt for rt in request_types if rt.name == name][0]
        except IndexError:
            raise KeyError(f"Request type '{name}' is unknown.")
        return request_type

    # User permissions

    # non-resource
    def my_permissions(
        self,
        projectKey: Optional[str] = None,
        projectId: Optional[str] = None,
        issueKey: Optional[str] = None,
        issueId: Optional[str] = None,
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Get a dict of all available permissions on the server.

        Args:
            projectKey (Optional[str]): limit returned permissions to the specified project
            projectId (Optional[str]): limit returned permissions to the specified project
            issueKey (Optional[str]): limit returned permissions to the specified issue
            issueId (Optional[str]): limit returned permissions to the specified issue

        Returns:
            Dict[str, Dict[str, Dict[str, str]]]
        """
        params = {}
        if projectKey is not None:
            params["projectKey"] = projectKey
        if projectId is not None:
            params["projectId"] = projectId
        if issueKey is not None:
            params["issueKey"] = issueKey
        if issueId is not None:
            params["issueId"] = issueId
        return self._get_json("mypermissions", params=params)

    # Priorities

    def priorities(self):
        """Get a list of priority Resources from the server.

        Returns:
            List[Priority]

        """
        r_json = self._get_json("priority")
        priorities = [
            Priority(self._options, self._session, raw_priority_json)
            for raw_priority_json in r_json
        ]
        return priorities

    def priority(self, id: str) -> Priority:
        """Get a priority Resource from the server.

        Args:
            id (str): ID of the priority to get

        Returns:
            Priority

        """
        return self._find_for_resource(Priority, id)

    # Projects

    def projects(self, expand: Optional[str] = None) -> List[Project]:
        """Get a list of project Resources from the server visible to the current authenticated user.

        Args:
            expand (Optional[str]): extra information to fetch for each project
                                    such as projectKeys and description.

        Returns:
            List[Project]

        """
        params = {}
        if expand is not None:
            params["expand"] = expand
        r_json = self._get_json("project", params=params)
        projects = [
            Project(self._options, self._session, raw_project_json)
            for raw_project_json in r_json
        ]
        return projects

    def project(self, id: str, expand: Optional[str] = None) -> Project:
        """Get a project Resource from the server.

        Args:
            id (str): ID or key of the project to get
            expand (Optional[str]): extra information to fetch for the project
                                    such as projectKeys and description.

        Returns:
            Project
        """
        return self._find_for_resource(Project, id, expand=expand)

    # non-resource
    @translate_resource_args
    def project_avatars(self, project: str):
        """Get a dict of all avatars for a project visible to the current authenticated user.

        Args:
            project (str): ID or key of the project to get avatars for
        """
        return self._get_json("project/" + project + "/avatars")

    @translate_resource_args
    def create_temp_project_avatar(
        self,
        project: str,
        filename: str,
        size: int,
        avatar_img: bytes,
        contentType: str = None,
        auto_confirm: bool = False,
    ):
        """Register an image file as a project avatar.

        The avatar created is temporary and must be confirmed before it can be used.

        Avatar images are specified by a filename, size, and file object. By default, the client will attempt to
        autodetect the picture's content type: this mechanism relies on libmagic and will not work out of the box
        on Windows systems (see https://filemagic.readthedocs.io/en/latest/guide.html for details on how to install
        support). The ``contentType`` argument can be used to explicitly set the value (note that Jira will reject any
        type other than the well-known ones for images, e.g. ``image/jpg``, ``image/png``, etc.)

        This method returns a dict of properties that can be used to crop a subarea of a larger image for use. This
        dict should be saved and passed to :py:meth:`confirm_project_avatar` to finish the avatar creation process. If
        you want to cut out the middleman and confirm the avatar with Jira's default cropping, pass the 'auto_confirm'
        argument with a truthy value and :py:meth:`confirm_project_avatar` will be called for you before this method
        returns.

        Args:
            project (str): ID or key of the project to create the avatar in
            filename (str): name of the avatar file
            size (int): size of the avatar file
            avatar_img (bytes): file-like object holding the avatar
            contentType (str): explicit specification for the avatar image's content-type
            auto_confirm (bool): whether to automatically confirm the temporary avatar by calling
              :py:meth:`confirm_project_avatar` with the return value of this method. (Default: False)
        """
        size_from_file = os.path.getsize(filename)
        if size != size_from_file:
            size = size_from_file

        params = {"filename": filename, "size": size}

        headers: Dict[str, Any] = {"X-Atlassian-Token": "no-check"}
        if contentType is not None:
            headers["content-type"] = contentType
        else:
            # try to detect content-type, this may return None
            headers["content-type"] = self._get_mime_type(avatar_img)

        url = self._get_url("project/" + project + "/avatar/temporary")
        r = self._session.post(url, params=params, headers=headers, data=avatar_img)

        cropping_properties: Dict[str, Any] = json_loads(r)
        if auto_confirm:
            return self.confirm_project_avatar(project, cropping_properties)
        else:
            return cropping_properties

    @translate_resource_args
    def confirm_project_avatar(self, project: str, cropping_properties: Dict[str, Any]):
        """Confirm the temporary avatar image previously uploaded with the specified cropping.

        After a successful registry with :py:meth:`create_temp_project_avatar`, use this method to confirm the avatar
        for use. The final avatar can be a subarea of the uploaded image, which is customized with the
        ``cropping_properties``: the return value of :py:meth:`create_temp_project_avatar` should be used for this
        argument.

        Args:
            project (str): ID or key of the project to confirm the avatar in
            cropping_properties (Dict[str,Any]): a dict of cropping properties from :py:meth:`create_temp_project_avatar`
        """
        data = cropping_properties
        url = self._get_url("project/" + project + "/avatar")
        r = self._session.post(url, data=json.dumps(data))

        return json_loads(r)

    @translate_resource_args
    def set_project_avatar(self, project: str, avatar: str):
        """Set a project's avatar.

        Args:
            project (str): ID or key of the project to set the avatar on
            avatar (str): ID of the avatar to set
        """
        self._set_avatar(None, self._get_url("project/" + project + "/avatar"), avatar)

    @translate_resource_args
    def delete_project_avatar(self, project: str, avatar: str) -> Response:
        """Delete a project's avatar.

        Args:
            project (str): ID or key of the project to delete the avatar from
            avatar (str): ID of the avatar to delete
        """
        url = self._get_url("project/" + project + "/avatar/" + avatar)
        return self._session.delete(url)

    @translate_resource_args
    def project_components(self, project: str) -> List[Component]:
        """Get a list of component Resources present on a project.

        Args:
            project (str): ID or key of the project to get components from

        Returns:
            List[Component]
        """
        r_json = self._get_json("project/" + project + "/components")
        components = [
            Component(self._options, self._session, raw_comp_json)
            for raw_comp_json in r_json
        ]
        return components

    @translate_resource_args
    def project_versions(self, project: str) -> List[Version]:
        """Get a list of version Resources present on a project.

        Args:
            project (str): ID or key of the project to get versions from

        Returns:
            List[Version]
        """
        r_json = self._get_json("project/" + project + "/versions")
        versions = [
            Version(self._options, self._session, raw_ver_json)
            for raw_ver_json in r_json
        ]
        return versions

    @translate_resource_args
    def get_project_version_by_name(
        self, project: str, version_name: str
    ) -> Optional[Version]:
        """Get a version Resource by its name present on a project.

        Args:
            project (str): ID or key of the project to get versions from
            version_name (str): name of the version to search for

        Returns:
            Optional[Version]
        """
        versions: List[Version] = self.project_versions(project)
        for version in versions:
            if version.name == version_name:
                return version
        return None

    @translate_resource_args
    def rename_version(self, project: str, old_name: str, new_name: str) -> None:
        """Rename a version Resource on a project.

        Args:
            project (str): ID or key of the project to get versions from
            old_name (str): old name of the version to rename
            new_name (str): new name of the version to rename

        Returns:
            None
        """
        version = self.get_project_version_by_name(project, old_name)
        if version:
            version.update(name=new_name)

    # non-resource
    @translate_resource_args
    def project_roles(self, project: str) -> Dict[str, Dict[str, str]]:
        """Get a dict of role names to resource locations for a project.

        Args:
            project (str): ID or key of the project to get roles from
        """
        path = "project/" + project + "/role"
        _rolesdict: Dict[str, str] = self._get_json(path)
        rolesdict: Dict[str, Dict[str, str]] = {}

        for k, v in _rolesdict.items():
            tmp: Dict[str, str] = {}
            tmp["id"] = v.split("/")[-1]
            tmp["url"] = v
            rolesdict[k] = tmp
        return rolesdict
        # TODO(ssbarnea): return a list of Roles()

    @translate_resource_args
    def project_role(self, project: str, id: str) -> Role:
        """Get a role Resource.

        Args:
            project (str): ID or key of the project to get the role from
            id (str): ID of the role to get
        """
        if isinstance(id, Number):
            id = f"{id}"
        return self._find_for_resource(Role, (project, id))

    # Resolutions

    def resolutions(self) -> List[Resolution]:
        """Get a list of resolution Resources from the server.

        Returns:
            List[Resolution]

        """
        r_json = self._get_json("resolution")
        resolutions = [
            Resolution(self._options, self._session, raw_res_json)
            for raw_res_json in r_json
        ]
        return resolutions

    def resolution(self, id: str) -> Resolution:
        """Get a resolution Resource from the server.

        Args:
            id (str): ID of the resolution to get

        Returns:
            Resolution
        """
        return self._find_for_resource(Resolution, id)

    # Search

    def search_issues(
        self,
        jql_str: str,
        startAt: int = 0,
        maxResults: int = 50,
        validate_query: bool = True,
        fields: Optional[Union[str, List[str]]] = None,
        expand: Optional[str] = None,
        json_result: bool = False,
    ) -> Union[List[Dict[str, Any]], ResultList[Issue]]:
        """Get a :class:`~jira.client.ResultList` of issue Resources matching a JQL search string.

        Args:
            jql_str (str): The JQL search string.
            startAt (int): Index of the first issue to return. (Default: 0)
            maxResults (int): Maximum number of issues to return. Total number of results
              is available in the ``total`` attribute of the returned :class:`~jira.client.ResultList`.
              If maxResults evaluates as False, it will try to get all issues in batches. (Default: 50)
            validate_query (bool): Whether or not the query should be validated. (Default: True)
            fields (Optional[Union[str, List[str]]]): comma-separated string or list of issue fields to include in the results.
              Default is to include all fields.
            expand (Optional[str]): extra information to fetch inside each resource
            json_result (bool): JSON response will be returned when this parameter is set to True.
              Otherwise, :class:`~jira.client.ResultList` will be returned.

        Returns:
            Union[Dict,ResultList]: Dict if ``json_result=True``

        """
        if isinstance(fields, str):
            fields = fields.split(",")
        else:
            fields = list(fields or [])

        # this will translate JQL field names to REST API Name
        # most people do know the JQL names so this will help them use the API easier
        untranslate = {}  # use to add friendly aliases when we get the results back
        if self._fields:
            for i, field in enumerate(fields):
                if field in self._fields:
                    untranslate[self._fields[field]] = fields[i]
                    fields[i] = self._fields[field]

        search_params = {
            "jql": jql_str,
            "startAt": startAt,
            "validateQuery": validate_query,
            "fields": fields,
            "expand": expand,
        }
        if json_result:
            search_params["maxResults"] = maxResults
            if not maxResults:
                warnings.warn(
                    "All issues cannot be fetched at once, when json_result parameter is set",
                    Warning,
                )
            r_json: List[Dict[str, Any]] = self._get_json(
                "search", params=search_params
            )
            return r_json

        issues = self._fetch_pages(
            Issue, "issues", "search", startAt, maxResults, search_params
        )

        if untranslate:
            iss: Issue
            for iss in issues:
                for k, v in untranslate.items():
                    if iss.raw:
                        if k in iss.raw.get("fields", {}):
                            iss.raw["fields"][v] = iss.raw["fields"][k]

        return issues

    # Security levels
    def security_level(self, id: str) -> SecurityLevel:
        """Get a security level Resource.

        Args:
            id (str): ID of the security level to get
        """
        return self._find_for_resource(SecurityLevel, id)

    # Server info

    # non-resource
    def server_info(self) -> Dict[str, Any]:
        """Get a dict of server information for this Jira instance.

        Returns:
            Dict[str, Any]
        """
        retry = 0
        j = self._get_json("serverInfo")
        while not j and retry < 3:
            self.log.warning(
                "Bug https://jira.atlassian.com/browse/JRA-59676 trying again..."
            )
            retry += 1
            j = self._get_json("serverInfo")
        return j

    def myself(self) -> Dict[str, Any]:
        """Get a dict of server information for this Jira instance."""
        return self._get_json("myself")

    # Status

    def statuses(self) -> List[Status]:
        """Get a list of status Resources from the server.

        Returns:
            List[Status]
        """
        r_json = self._get_json("status")
        statuses = [
            Status(self._options, self._session, raw_stat_json)
            for raw_stat_json in r_json
        ]
        return statuses

    def status(self, id: str) -> Status:
        """Get a status Resource from the server.

        Args:
            id (str): ID of the status resource to get

        Returns:
            Status
        """
        return self._find_for_resource(Status, id)

    # Category

    def statuscategories(self) -> List[StatusCategory]:
        """Get a list of status category Resources from the server.

        Returns:
            List[StatusCategory]
        """
        r_json = self._get_json("statuscategory")
        statuscategories = [
            StatusCategory(self._options, self._session, raw_stat_json)
            for raw_stat_json in r_json
        ]
        return statuscategories

    def statuscategory(self, id: int) -> StatusCategory:
        """Get a status category Resource from the server.

        Args:
            id (int): ID of the status category resource to get

        Returns:
            StatusCategory

        """
        return self._find_for_resource(StatusCategory, id)

    # Users

    def user(self, id: str, expand: Optional[Any] = None) -> User:
        """Get a user Resource from the server.

        Args:
            id (str): ID of the user to get
            expand (Optional[Any]): Extra information to fetch inside each resource

        Returns:
            User
        """
        user = User(self._options, self._session)
        params = {}
        if expand is not None:
            params["expand"] = expand
        user.find(id, params=params)
        return user

    def search_assignable_users_for_projects(
        self, username: str, projectKeys: str, startAt: int = 0, maxResults: int = 50
    ) -> ResultList:
        """Get a list of user Resources that match the search string and can be assigned issues for projects.

        Args:
            username (str): A string to match usernames against
            projectKeys (str): Comma-separated list of project keys to check for issue assignment permissions
            startAt (int): Index of the first user to return (Default: 0)
            maxResults (int): Maximum number of users to return.
              If maxResults evaluates as False, it will try to get all users in batches. (Default: 50)

        Returns:
            ResultList

        """
        params = {"username": username, "projectKeys": projectKeys}
        return self._fetch_pages(
            User,
            None,
            "user/assignable/multiProjectSearch",
            startAt,
            maxResults,
            params,
        )

    def search_assignable_users_for_issues(
        self,
        username: str,
        project: Optional[str] = None,
        issueKey: Optional[str] = None,
        expand: Optional[Any] = None,
        startAt: int = 0,
        maxResults: int = 50,
    ):
        """Get a list of user Resources that match the search string for assigning or creating issues.

        This method is intended to find users that are eligible to create issues in a project or be assigned
        to an existing issue. When searching for eligible creators, specify a project. When searching for eligible
        assignees, specify an issue key.

        Args:
            username (str): A string to match usernames against
            project (Optional[str]): Filter returned users by permission in this project
              (expected if a result will be used to create an issue)
            issueKey (Optional[str]): Filter returned users by this issue
              (expected if a result will be used to edit this issue)
            expand (Optional[Any]): Extra information to fetch inside each resource
            startAt (int): Index of the first user to return (Default: 0)
            maxResults (int): maximum number of users to return.
              If maxResults evaluates as False, it will try to get all items in batches. (Default: 50)

        Returns:
            ResultList
        """
        params = {"username": username}
        if project is not None:
            params["project"] = project
        if issueKey is not None:
            params["issueKey"] = issueKey
        if expand is not None:
            params["expand"] = expand
        return self._fetch_pages(
            User, None, "user/assignable/search", startAt, maxResults, params
        )

    # non-resource
    def user_avatars(self, username: str) -> Dict[str, Any]:
        """Get a dict of avatars for the specified user.

        Args:
            username (str): the username to get avatars for
        """
        return self._get_json("user/avatars", params={"username": username})

    def create_temp_user_avatar(
        self,
        user: str,
        filename: str,
        size: int,
        avatar_img: bytes,
        contentType: Any = None,
        auto_confirm: bool = False,
    ):
        """Register an image file as a user avatar.

        The avatar created is temporary and must be confirmed before it can
        be used.

        Avatar images are specified by a filename, size, and file object. By default, the client will attempt to
        autodetect the picture's content type: this mechanism relies on ``libmagic`` and will not work out of the box
        on Windows systems (see http://filemagic.readthedocs.org/en/latest/guide.html for details on how to install
        support). The ``contentType`` argument can be used to explicitly set the value (note that Jira will reject any
        type other than the well-known ones for images, e.g. ``image/jpg``, ``image/png``, etc.)

        This method returns a dict of properties that can be used to crop a subarea of a larger image for use. This
        dict should be saved and passed to :py:meth:`confirm_user_avatar` to finish the avatar creation process. If you
        want to cut out the middleman and confirm the avatar with Jira's default cropping, pass the ``auto_confirm``
        argument with a truthy value and :py:meth:`confirm_user_avatar` will be called for you before this method
        returns.

        Args:
            user (str): User to register the avatar for
            filename (str): name of the avatar file
            size (int): size of the avatar file
            avatar_img (bytes): file-like object containing the avatar
            contentType (Optional[Any]): explicit specification for the avatar image's content-type
            auto_confirm (bool): whether to automatically confirm the temporary avatar by calling
              :py:meth:`confirm_user_avatar` with the return value of this method. (Default: False)

        """
        size_from_file = os.path.getsize(filename)
        if size != size_from_file:
            size = size_from_file

        # remove path from filename
        filename = os.path.split(filename)[1]

        params = {"username": user, "filename": filename, "size": size}

        headers: Dict[str, Any]
        headers = {"X-Atlassian-Token": "no-check"}
        if contentType is not None:
            headers["content-type"] = contentType
        else:
            # try to detect content-type, this may return None
            headers["content-type"] = self._get_mime_type(avatar_img)

        url = self._get_url("user/avatar/temporary")
        r = self._session.post(url, params=params, headers=headers, data=avatar_img)

        cropping_properties: Dict[str, Any] = json_loads(r)
        if auto_confirm:
            return self.confirm_user_avatar(user, cropping_properties)
        else:
            return cropping_properties

    def confirm_user_avatar(self, user: str, cropping_properties: Dict[str, Any]):
        """Confirm the temporary avatar image previously uploaded with the specified cropping.

        After a successful registry with :py:meth:`create_temp_user_avatar`, use this method to confirm the avatar for
        use. The final avatar can be a subarea of the uploaded image, which is customized with the
        ``cropping_properties``: the return value of :py:meth:`create_temp_user_avatar` should be used for this
        argument.

        Args:
            user (str): the user to confirm the avatar for
            cropping_properties (Dict[str,Any]): a dict of cropping properties from :py:meth:`create_temp_user_avatar`
        """
        data = cropping_properties
        url = self._get_url("user/avatar")
        r = self._session.post(url, params={"username": user}, data=json.dumps(data))

        return json_loads(r)

    def set_user_avatar(self, username: str, avatar: str) -> Response:
        """Set a user's avatar.

        Args:
            username (str): the user to set the avatar for
            avatar (str): ID of the avatar to set
        """
        return self._set_avatar(
            {"username": username}, self._get_url("user/avatar"), avatar
        )

    def delete_user_avatar(self, username: str, avatar: str):
        """Delete a user's avatar.

        Args:
            username (str): the user to delete the avatar from
            avatar (str): ID of the avatar to remove
        """
        params = {"username": username}
        url = self._get_url("user/avatar/" + avatar)
        return self._session.delete(url, params=params)

    def search_users(
        self,
        user: Optional[str] = None,
        startAt: int = 0,
        maxResults: int = 50,
        includeActive: bool = True,
        includeInactive: bool = False,
        query: Optional[str] = None,
    ) -> ResultList[User]:
        """Get a list of user Resources that match the specified search string.
        "username" query parameter is deprecated in Jira Cloud; the expected parameter now is "query", which can just be the full
        email again. But the "user" parameter is kept for backwards compatibility, i.e. Jira Server/Data Center.

        Args:
            user (Optional[str]): a string to match usernames, name or email against.
            startAt (int): index of the first user to return.
            maxResults (int): maximum number of users to return.
              If maxResults evaluates as False, it will try to get all items in batches.
            includeActive (bool): If true, then active users are included in the results. (Default: True)
            includeInactive (bool): If true, then inactive users are included in the results. (Default: False)
            query (Optional[str]): Search term. It can just be the email.

        Returns:
            ResultList[User]
        """
        if not user and not query:
            raise ValueError("Either 'user' or 'query' arguments must be specified.")

        params = {
            "username": user,
            "query": query,
            "includeActive": includeActive,
            "includeInactive": includeInactive,
        }

        return self._fetch_pages(User, None, "user/search", startAt, maxResults, params)

    def search_allowed_users_for_issue(
        self,
        user: str,
        issueKey: str = None,
        projectKey: str = None,
        startAt: int = 0,
        maxResults: int = 50,
    ) -> ResultList:
        """Get a list of user Resources that match a username string and have browse permission for the issue or project.

        Args:
            user (str): a string to match usernames against.
            issueKey (Optional[str]): find users with browse permission for this issue.
            projectKey (Optional[str]): find users with browse permission for this project.
            startAt (int): index of the first user to return. (Default: 0)
            maxResults (int): maximum number of users to return.
              If maxResults evaluates as False, it will try to get all items in batches. (Default: 50)

        Returns:
            ResultList
        """
        params = {"username": user}
        if issueKey is not None:
            params["issueKey"] = issueKey
        if projectKey is not None:
            params["projectKey"] = projectKey
        return self._fetch_pages(
            User, None, "user/viewissue/search", startAt, maxResults, params
        )

    # Versions

    @translate_resource_args
    def create_version(
        self,
        name: str,
        project: str,
        description: str = None,
        releaseDate: Any = None,
        startDate: Any = None,
        archived: bool = False,
        released: bool = False,
    ) -> Version:
        """Create a version in a project and return a Resource for it.

        Args:
            name (str): name of the version to create
            project (str): key of the project to create the version in
            description (str): a description of the version
            releaseDate (Optional[Any]): the release date assigned to the version
            startDate (Optional[Any]): The start date for the version
            archived (bool): Denotes whether a version should be archived. (Default: False)
            released (bool): Denotes whether a version is released. (Default: False)

        Returns:
            Version
        """
        data = {
            "name": name,
            "project": project,
            "archived": archived,
            "released": released,
        }
        if description is not None:
            data["description"] = description
        if releaseDate is not None:
            data["releaseDate"] = releaseDate
        if startDate is not None:
            data["startDate"] = startDate

        url = self._get_url("version")
        r = self._session.post(url, data=json.dumps(data))

        time.sleep(1)
        version = Version(self._options, self._session, raw=json_loads(r))
        return version

    def move_version(self, id: str, after: str = None, position: str = None) -> Version:
        """Move a version within a project's ordered version list and return a new version Resource for it.

        One, but not both, of ``after`` and ``position`` must be specified.

        Args:
            id (str): ID of the version to move
            after (str): the self attribute of a version to place the specified version after (that is, higher in the list)
            position (Optional[str]): the absolute position to move this version to:
              must be one of ``First``, ``Last``, ``Earlier``, or ``Later``

        Returns:
            Version
        """
        data = {}
        if after is not None:
            data["after"] = after
        elif position is not None:
            data["position"] = position

        url = self._get_url("version/" + id + "/move")
        r = self._session.post(url, data=json.dumps(data))

        version = Version(self._options, self._session, raw=json_loads(r))
        return version

    def version(self, id: str, expand: Any = None) -> Version:
        """Get a version Resource.

        Args:
            id (str): ID of the version to get
            expand (Optional[Any]): extra information to fetch inside each resource

        Returns:
            Version
        """
        version = Version(self._options, self._session)
        params = {}
        if expand is not None:
            params["expand"] = expand
        version.find(id, params=params)
        return version

    def version_count_related_issues(self, id: str):
        """Get a dict of the counts of issues fixed and affected by a version.

        Args:
            id (str): the version to count issues for
        """
        r_json: Dict[str, Any] = self._get_json("version/" + id + "/relatedIssueCounts")
        del r_json["self"]  # this isn't really an addressable resource
        return r_json

    def version_count_unresolved_issues(self, id: str):
        """Get the number of unresolved issues for a version.

        Args:
            id (str): ID of the version to count issues for
        """
        r_json: Dict[str, Any] = self._get_json(
            "version/" + id + "/unresolvedIssueCount"
        )
        return r_json["issuesUnresolvedCount"]

    # Session authentication

    def session(self) -> User:
        """Get a dict of the current authenticated user's session information.

        Returns:
            User
        """
        url = "{server}{auth_url}".format(**self._options)
        r = self._session.get(url)

        user = User(self._options, self._session, json_loads(r))
        return user

    def kill_session(self) -> Response:
        """Destroy the session of the current authenticated user."""
        url = self.server_url + "/rest/auth/latest/session"
        return self._session.delete(url)

    # Websudo
    def kill_websudo(self) -> Optional[Response]:
        """Destroy the user's current WebSudo session.

        Works only for non-cloud deployments, for others does nothing.

        Returns:
            Optional[Response]
        """
        if not self._is_cloud:
            url = self.server_url + "/rest/auth/1/websudo"
            return self._session.delete(url)
        return None

    # Utilities
    def _create_http_basic_session(
        self,
        username: str,
        password: str,
        timeout: Optional[Union[Union[float, int], Tuple[float, float]]] = None,
    ):
        """Creates a basic http session.

        Args:
            username (str): Username for the session
            password (str): Password for the username
            timeout (Optional[int]): If set determines the timeout period for the Session.

        Returns:
            ResilientSession
        """
        verify = bool(self._options["verify"])
        self._session = ResilientSession(timeout=timeout)
        self._session.verify = verify
        self._session.auth = (username, password)
        client_cert: Tuple[str, str] = self._options["client_cert"]  # to help mypy
        self._session.cert = client_cert

    def _create_oauth_session(
        self, oauth, timeout: Optional[Union[Union[float, int], Tuple[float, float]]]
    ):
        verify = bool(self._options["verify"])

        from oauthlib.oauth1 import SIGNATURE_RSA
        from requests_oauthlib import OAuth1

        oauth_instance = OAuth1(
            oauth["consumer_key"],
            rsa_key=oauth["key_cert"],
            signature_method=SIGNATURE_RSA,
            resource_owner_key=oauth["access_token"],
            resource_owner_secret=oauth["access_token_secret"],
        )
        self._session = ResilientSession(timeout)
        self._session.verify = verify
        self._session.auth = oauth_instance

    def _create_kerberos_session(
        self,
        timeout: Optional[Union[Union[float, int], Tuple[float, float]]],
        kerberos_options=None,
    ):
        verify = bool(self._options["verify"])
        if kerberos_options is None:
            kerberos_options = {}

        from requests_kerberos import DISABLED, OPTIONAL, HTTPKerberosAuth

        if kerberos_options.get("mutual_authentication", "OPTIONAL") == "OPTIONAL":
            mutual_authentication = OPTIONAL
        elif kerberos_options.get("mutual_authentication") == "DISABLED":
            mutual_authentication = DISABLED
        else:
            raise ValueError(
                "Unknown value for mutual_authentication: %s"
                % kerberos_options["mutual_authentication"]
            )

        self._session = ResilientSession(timeout=timeout)
        self._session.verify = verify
        self._session.auth = HTTPKerberosAuth(
            mutual_authentication=mutual_authentication
        )

    @staticmethod
    def _timestamp(dt: datetime.timedelta = None):
        t = datetime.datetime.utcnow()
        if dt is not None:
            t += dt
        return calendar.timegm(t.timetuple())

    def _create_jwt_session(
        self, jwt, timeout: Optional[Union[Union[float, int], Tuple[float, float]]]
    ):
        try:
            jwt_auth = JWTAuth(jwt["secret"], alg="HS256")
        except NameError as e:
            self.log.error("JWT authentication requires requests_jwt")
            raise e
        jwt_auth.set_header_format("JWT %s")

        jwt_auth.add_field("iat", lambda req: JIRA._timestamp())
        jwt_auth.add_field(
            "exp", lambda req: JIRA._timestamp(datetime.timedelta(minutes=3))
        )
        jwt_auth.add_field("qsh", QshGenerator(self._options["context_path"]))
        for f in jwt["payload"].items():
            jwt_auth.add_field(f[0], f[1])
        self._session = ResilientSession(timeout=timeout)
        self._session.verify = bool(self._options["verify"])
        self._session.auth = jwt_auth

    def _set_avatar(self, params, url, avatar):
        data = {"id": avatar}
        return self._session.put(url, params=params, data=json.dumps(data))

    def _get_url(self, path: str, base: str = JIRA_BASE_URL) -> str:
        """Returns the full url based on Jira base url and the path provided.
        Using the API version specified during the __init__.

        Args:
            path (str): The subpath desired.
            base (Optional[str]): The base url which should be prepended to the path

        Returns:
            str: Fully qualified URL
        """
        options = self._options.copy()
        options.update({"path": path})
        return base.format(**options)

    def _get_latest_url(self, path: str, base: str = JIRA_BASE_URL) -> str:
        """Returns the full url based on Jira base url and the path provided.
        Using the latest API endpoint.

        Args:
            path (str): The subpath desired.
            base (Optional[str]): The base url which should be prepended to the path

        Returns:
            str: Fully qualified URL
        """
        options = self._options.copy()
        options.update({"path": path, "rest_api_version": "latest"})
        return base.format(**options)

    def _get_json(
        self, path: str, params: Dict[str, Any] = None, base: str = JIRA_BASE_URL
    ):
        """Get the json for a given path and params.

        Args:
            path (str): The subpath required
            params (Optional[Dict[str, Any]]): Parameters to filter the json query.
            base (Optional[str]): The Base Jira URL, defaults to the instance base.

        Returns:
            Union[Dict[str, Any], List[Dict[str, str]]]

        """
        url = self._get_url(path, base)
        r = self._session.get(url, params=params)
        try:
            r_json = json_loads(r)
        except ValueError as e:
            self.log.error(f"{e}\n{r.text if r else r}")
            raise e
        return r_json

    def _find_for_resource(
        self, resource_cls: Any, ids: Union[Tuple[str, str], int, str], expand=None
    ) -> Any:
        """Uses the find method of the provided Resource class

        Args:
            resource_cls (Any): Any instance of :py:class`Resource`
            ids (Union[Tuple[str, str], int, str]): The arguments to the Resource's ``find()``
            expand ([type], optional): The value for the expand property in the Resource's
              ``find()`` params. Defaults to None.

        Raises:
            JIRAError: If the Resource cannot be found

        Returns:
            Any: A class of the same type as ``resource_cls``
        """
        resource = resource_cls(self._options, self._session)
        params = {}
        if expand is not None:
            params["expand"] = expand
        resource.find(id=ids, params=params)
        if not resource:
            raise JIRAError("Unable to find resource %s(%s)", resource_cls, str(ids))
        return resource

    def _try_magic(self):
        try:
            import weakref

            import magic
        except ImportError:
            self._magic = None
        else:
            try:
                _magic = magic.Magic(flags=magic.MAGIC_MIME_TYPE)

                def cleanup(x):
                    _magic.close()

                self._magic_weakref = weakref.ref(self, cleanup)
                self._magic = _magic
            except TypeError:
                self._magic = None
            except AttributeError:
                self._magic = None

    def _get_mime_type(self, buff: bytes) -> Optional[str]:
        """Get the MIME type for a given stream of bytes

        Args:
            buff (bytes): Stream of bytes

        Returns:
            Optional[str]: the MIME type

        """
        if self._magic is not None:
            return self._magic.id_buffer(buff)
        else:
            try:
                return mimetypes.guess_type("f." + str(imghdr.what(0, buff)))[0]
            except (IOError, TypeError):
                self.log.warning(
                    "Couldn't detect content type of avatar image"
                    ". Specify the 'contentType' parameter explicitly."
                )
                return None

    def rename_user(self, old_user: str, new_user: str):
        """Rename a Jira user.

        Args:
            old_user (str): Old username login
            new_user (str): New username login

        """
        if self._version > (6, 0, 0):
            url = self._get_latest_url("user")
            payload = {"name": new_user}
            params = {"username": old_user}

            # raw displayName
            self.log.debug(f"renaming {self.user(old_user).emailAddress}")

            r = self._session.put(url, params=params, data=json.dumps(payload))
            raise_on_error(r)
        else:
            raise NotImplementedError(
                "Support for renaming users in Jira " "< 6.0.0 has been removed."
            )

    def delete_user(self, username: str) -> bool:
        """Deletes a Jira User.

        Args:
            username (str): Username to delete

        Returns:
            bool: Success of user deletion

        """

        url = self._get_latest_url(f"user/?username={username}")

        r = self._session.delete(url)
        if 200 <= r.status_code <= 299:
            return True
        else:
            self.log.error(r.status_code)
            return False

    def deactivate_user(self, username: str) -> Union[str, int]:
        """Disable/deactivate the user.

        Args:
            username (str): User to be deactivated.

        Returns:
            Union[str, int]
        """
        if self._is_cloud:
            # Disabling users now needs cookie auth in the Cloud - see https://jira.atlassian.com/browse/ID-6230
            if "authCookie" not in vars(self):
                user = self.session()
                if user.raw is None:
                    raise JIRAError("Can not log in!")
                self.authCookie = "%s=%s" % (
                    user.raw["session"]["name"],
                    user.raw["session"]["value"],
                )
            url = (
                self._options["server"]
                + f"/admin/rest/um/1/user/deactivate?username={username}"
            )
            # We can't use our existing session here - this endpoint is fragile and objects to extra headers
            try:
                r = requests.post(
                    url,
                    headers={
                        "Cookie": self.authCookie,
                        "Content-Type": "application/json",
                    },
                    proxies=self._session.proxies,
                    data={},
                )
                if r.status_code == 200:
                    return True
                else:
                    self.log.warning(
                        f"Got response from deactivating {username}: {r.status_code}"
                    )
                    return r.status_code
            except Exception as e:
                self.log.error(f"Error Deactivating {username}: {e}")
                raise JIRAError(f"Error Deactivating {username}: {e}")
        else:
            url = self.server_url + "/secure/admin/user/EditUser.jspa"
            self._options["headers"][
                "Content-Type"
            ] = "application/x-www-form-urlencoded; charset=UTF-8"
            user = self.user(username)
            userInfo = {
                "inline": "true",
                "decorator": "dialog",
                "username": user.name,
                "fullName": user.displayName,
                "email": user.emailAddress,
                "editName": user.name,
            }
            try:
                r = self._session.post(
                    url, headers=self._options["headers"], data=userInfo
                )
                if r.status_code == 200:
                    return True
                else:
                    self.log.warning(
                        f"Got response from deactivating {username}: {r.status_code}"
                    )
                    return r.status_code
            except Exception as e:
                self.log.error(f"Error Deactivating {username}: {e}")
                raise JIRAError(f"Error Deactivating {username}: {e}")

    def reindex(self, force: bool = False, background: bool = True) -> bool:
        """Start jira re-indexing. Returns True if reindexing is in progress or not needed, or False.

        If you call reindex() without any parameters it will perform a background reindex only if Jira thinks it should do it.

        Args:
            force (bool): reindex even if Jira doesn't say this is needed, False by default.
            background (bool): reindex in background, slower but does not impact the users, defaults to True.

        Returns:
            bool: Returns True if reindexing is in progress or not needed, or False.
        """
        # /secure/admin/IndexAdmin.jspa
        # /secure/admin/jira/IndexProgress.jspa?taskId=1
        if background:
            indexingStrategy = "background"
        else:
            indexingStrategy = "stoptheworld"

        url = self.server_url + "/secure/admin/jira/IndexReIndex.jspa"

        r = self._session.get(url, headers=self._options["headers"])
        if r.status_code == 503:
            # self.log.warning("Jira returned 503, this could mean that a full reindex is in progress.")
            return 503  # type: ignore # FIXME: is this a bug?

        if (
            not r.text.find("To perform the re-index now, please go to the")
            and force is False
        ):
            return True

        if r.text.find("All issues are being re-indexed"):
            self.log.warning("Jira re-indexing is already running.")
            return True  # still reindexing is considered still a success

        if r.text.find("To perform the re-index now, please go to the") or force:
            r = self._session.post(
                url,
                headers=self._options["headers"],
                params={"indexingStrategy": indexingStrategy, "reindex": "Re-Index"},
            )
            if r.text.find("All issues are being re-indexed") != -1:
                return True

        self.log.error("Failed to reindex jira, probably a bug.")
        return False

    def backup(self, filename: str = "backup.zip", attachments: bool = False):
        """Will call jira export to backup as zipped xml. Returning with success does not mean that the backup process finished."""
        payload: Any  # _session.post is pretty open
        if self._is_cloud:
            url = self.server_url + "/rest/backup/1/export/runbackup"
            payload = json.dumps({"cbAttachments": attachments})
            self._options["headers"]["X-Requested-With"] = "XMLHttpRequest"
        else:
            url = self.server_url + "/secure/admin/XmlBackup.jspa"
            payload = {"filename": filename}
        try:
            r = self._session.post(url, headers=self._options["headers"], data=payload)
            if r.status_code == 200:
                return True
            else:
                self.log.warning(f"Got {r.status_code} response from calling backup.")
                return r.status_code
        except Exception as e:
            self.log.error("I see %s", e)

    def backup_progress(self):
        """Return status of cloud backup as a dict.

        Is there a way to get progress for Server version?
        """
        epoch_time = int(time.time() * 1000)
        if self._is_cloud:
            url = self.server_url + "/rest/obm/1.0/getprogress?_=%i" % epoch_time
        else:
            self.log.warning("This functionality is not available in Server version")
            return None
        r = self._session.get(url, headers=self._options["headers"])
        # This is weird.  I used to get xml, but now I'm getting json
        try:
            return json.loads(r.text)
        except Exception:
            import defusedxml.ElementTree as etree

            progress = {}
            try:
                root = etree.fromstring(r.text)
            except etree.ParseError as pe:
                self.log.warning(
                    "Unable to find backup info.  You probably need to initiate a new backup. %s"
                    % pe
                )
                return None
            for k in root.keys():
                progress[k] = root.get(k)
            return progress

    def backup_complete(self) -> Optional[bool]:
        """Return boolean based on 'alternativePercentage' and 'size' returned from backup_progress (cloud only)."""
        if not self._is_cloud:
            self.log.warning("This functionality is not available in Server version")
            return None
        status = self.backup_progress()
        perc_search = re.search(r"\s([0-9]*)\s", status["alternativePercentage"])
        perc_complete = int(
            perc_search.group(1)  # type: ignore # ignore that re.search can return None
        )
        file_size = int(status["size"])
        return perc_complete >= 100 and file_size > 0

    def backup_download(self, filename: str = None):
        """Download backup file from WebDAV (cloud only)."""
        if not self._is_cloud:
            self.log.warning("This functionality is not available in Server version")
            return None
        remote_file = self.backup_progress()["fileName"]
        local_file = filename or remote_file
        url = self.server_url + "/webdav/backupmanager/" + remote_file
        try:
            self.log.debug(f"Writing file to {local_file}")
            with open(local_file, "wb") as file:
                try:
                    resp = self._session.get(
                        url, headers=self._options["headers"], stream=True
                    )
                except Exception:
                    raise JIRAError()
                if not resp.ok:
                    self.log.error(f"Something went wrong with download: {resp.text}")
                    raise JIRAError(resp.text)
                for block in resp.iter_content(1024):
                    file.write(block)
        except JIRAError as je:
            self.log.error(f"Unable to access remote backup file: {je}")
        except IOError as ioe:
            self.log.error(ioe)
        return None

    def current_user(self, field: str = "key") -> str:
        """Returns the username or emailAddress of the current user. For anonymous
        users it will return a value that evaluates as False.

        Returns:
            str
        """
        if not hasattr(self, "_myself"):

            url = self._get_url("myself")
            r = self._session.get(url, headers=self._options["headers"])

            r_json: Dict[str, str] = json_loads(r)
            self._myself = r_json

        return self._myself[field]

    def delete_project(self, pid: Union[str, Project]) -> Optional[bool]:
        """Delete project from Jira.

        Args:
            pid (Union[str, Project]): Jira projectID or Project or slug

        Raises:
            JIRAError:  If project not found or not enough permissions
            ValueError: If pid parameter is not Project, slug or ProjectID

        Returns:
            bool: True if project was deleted
        """
        # allows us to call it with Project objects
        if isinstance(pid, Project) and hasattr(pid, "id"):
            pid = str(pid.id)

        url = self._get_url(f"project/{pid}")
        r = self._session.delete(url)
        if r.status_code == 403:
            raise JIRAError("Not enough permissions to delete project")
        if r.status_code == 404:
            raise JIRAError("Project not found in Jira")
        return r.ok

    def _gain_sudo_session(self, options, destination):
        url = self.server_url + "/secure/admin/WebSudoAuthenticate.jspa"

        if not self._session.auth:
            self._session.auth = get_netrc_auth(url)

        payload = {
            "webSudoPassword": self._session.auth[1],
            "webSudoDestination": destination,
            "webSudoIsPost": "true",
        }

        payload.update(options)

        return self._session.post(
            url,
            headers=CaseInsensitiveDict(
                {"content-type": "application/x-www-form-urlencoded"}
            ),
            data=payload,
        )

    @lru_cache(maxsize=None)
    def templates(self) -> Dict:

        url = self.server_url + "/rest/project-templates/latest/templates"

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)

        templates = {}
        if "projectTemplatesGroupedByType" in data:
            for group in data["projectTemplatesGroupedByType"]:
                for t in group["projectTemplates"]:
                    templates[t["name"]] = t
        # pprint(templates.keys())
        return templates

    @lru_cache(maxsize=None)
    def permissionschemes(self):

        url = self._get_url("permissionscheme")

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)

        return data["permissionSchemes"]

    @lru_cache(maxsize=None)
    def issuesecurityschemes(self):

        url = self._get_url("issuesecurityschemes")

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)

        return data["issueSecuritySchemes"]

    @lru_cache(maxsize=None)
    def projectcategories(self):

        url = self._get_url("projectCategory")

        r = self._session.get(url)
        data = json_loads(r)

        return data

    @lru_cache(maxsize=None)
    def avatars(self, entity="project"):

        url = self._get_url(f"avatar/{entity}/system")

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)

        return data["system"]

    @lru_cache(maxsize=None)
    def notificationschemes(self):
        # TODO(ssbarnea): implement pagination support
        url = self._get_url("notificationscheme")

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)
        return data["values"]

    @lru_cache(maxsize=None)
    def screens(self):
        # TODO(ssbarnea): implement pagination support
        url = self._get_url("screens")

        r = self._session.get(url)
        data: Dict[str, Any] = json_loads(r)
        return data["values"]

    @lru_cache(maxsize=None)
    def workflowscheme(self):
        # TODO(ssbarnea): implement pagination support
        url = self._get_url("workflowschemes")

        r = self._session.get(url)
        data = json_loads(r)
        return data  # ['values']

    @lru_cache(maxsize=None)
    def workflows(self):
        # TODO(ssbarnea): implement pagination support
        url = self._get_url("workflow")

        r = self._session.get(url)
        data = json_loads(r)
        return data  # ['values']

    def delete_screen(self, id: str):

        url = self._get_url(f"screens/{id}")

        r = self._session.delete(url)
        data = json_loads(r)

        self.screens.cache_clear()
        return data

    def delete_permissionscheme(self, id: str):

        url = self._get_url(f"permissionscheme/{id}")

        r = self._session.delete(url)
        data = json_loads(r)

        self.permissionschemes.cache_clear()
        return data

    def create_project(
        self,
        key: str,
        name: str = None,
        assignee: str = None,
        ptype: str = "software",
        template_name: str = None,
        avatarId=None,
        issueSecurityScheme=None,
        permissionScheme=None,
        projectCategory=None,
        notificationScheme=10000,
        categoryId=None,
        url: str = "",
    ):
        """Create a project with the specified parameters.

        Args:
            key (str): Mandatory. Must match Jira project key requirements, usually only 2-10 uppercase characters.
            name (Optional[str]): If not specified it will use the key value.
            assignee (Optional[str]): key of the lead, if not specified it will use current user.
            ptype (Optional[str]): Determines the type of project should be created.
            template_name (Optional[str]): is used to create a project based on one of the existing project templates.
              If `template_name` is not specified, then it should use one of the default values.

        Returns:
            Union[bool,int]: Should evaluate to False if it fails otherwise it will be the new project id.

        """
        template_key = None

        if assignee is None:
            assignee = self.current_user()
        if name is None:
            name = key

        ps_list: List[Dict[str, Any]]

        if not permissionScheme:
            ps_list = self.permissionschemes()
            for sec in ps_list:
                if sec["name"] == "Default Permission Scheme":
                    permissionScheme = sec["id"]
                break
            if not permissionScheme:
                permissionScheme = ps_list[0]["id"]

        if not issueSecurityScheme:
            ps_list = self.issuesecurityschemes()
            for sec in ps_list:
                if sec["name"] == "Default":  # no idea which one is default
                    issueSecurityScheme = sec["id"]
                break
            if not issueSecurityScheme and ps_list:
                issueSecurityScheme = ps_list[0]["id"]

        if not projectCategory:
            ps_list = self.projectcategories()
            for sec in ps_list:
                if sec["name"] == "Default":  # no idea which one is default
                    projectCategory = sec["id"]
                break
            if not projectCategory and ps_list:
                projectCategory = ps_list[0]["id"]
        # <beep> Atlassian for failing to provide an API to get projectTemplateKey values
        #  Possible values are just hardcoded and obviously depending on Jira version.
        # https://developer.atlassian.com/cloud/jira/platform/rest/v3/?_ga=2.88310429.766596084.1562439833-992274574.1559129176#api-rest-api-3-project-post
        # https://jira.atlassian.com/browse/JRASERVER-59658
        # preference list for picking a default template
        if not template_name:
            # https://confluence.atlassian.com/jirakb/creating-projects-via-rest-api-in-jira-963651978.html
            template_key = (
                "com.pyxis.greenhopper.jira:basic-software-development-template"
            )

        # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-projects/#api-rest-api-2-project-get
        # template_keys = [
        #     "com.pyxis.greenhopper.jira:gh-simplified-agility-kanban",
        #     "com.pyxis.greenhopper.jira:gh-simplified-agility-scrum",
        #     "com.pyxis.greenhopper.jira:gh-simplified-basic",
        #     "com.pyxis.greenhopper.jira:gh-simplified-kanban-classic",
        #     "com.pyxis.greenhopper.jira:gh-simplified-scrum-classic",
        #     "com.atlassian.servicedesk:simplified-it-service-desk",
        #     "com.atlassian.servicedesk:simplified-internal-service-desk",
        #     "com.atlassian.servicedesk:simplified-external-service-desk",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-content-management",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-document-approval",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-lead-tracking",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-process-control",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-procurement",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-project-management",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-recruitment",
        #     "com.atlassian.jira-core-project-templates:jira-core-simplified-task-",
        #     "com.atlassian.jira.jira-incident-management-plugin:im-incident-management",
        # ]

        # possible_templates = [
        #     "Scrum software development",  # have Bug
        #     "Agility",  # cannot set summary
        #     "Bug tracking",
        #     "JIRA Classic",
        #     "JIRA Default Schemes",
        #     "Basic software development",
        #     "Project management",
        #     "Kanban software development",
        #     "Task management",
        #     "Basic",  # does not have Bug
        #     "Content Management",
        #     "Customer service",
        #     "Document Approval",
        #     "IT Service Desk",
        #     "Lead Tracking",
        #     "Process management",
        #     "Procurement",
        #     "Recruitment",
        # ]

        # templates = self.templates()
        # if not template_name:
        #     for k, v in templates.items():
        #         if v['projectTypeKey'] == type:
        #             template_name = k

        # template_name = next((t for t in templates if t['projectTypeKey'] == 'x'))

        # template_key = templates[template_name]["projectTemplateModuleCompleteKey"]
        # project_type_key = templates[template_name]["projectTypeKey"]

        # https://confluence.atlassian.com/jirakb/creating-a-project-via-rest-based-on-jira-default-schemes-744325852.html
        # see https://confluence.atlassian.com/jirakb/creating-projects-via-rest-api-in-jira-963651978.html
        payload = {
            "name": name,
            "key": key,
            "projectTypeKey": ptype,
            "projectTemplateKey": template_key,
            "lead": assignee,
            # "leadAccountId": assignee,
            "assigneeType": "PROJECT_LEAD",
            "description": "",
            # "avatarId": 13946,
            "permissionScheme": int(permissionScheme),
            "notificationScheme": notificationScheme,
            "url": url,
        }
        if issueSecurityScheme:
            payload["issueSecurityScheme"] = int(issueSecurityScheme)
        if projectCategory:
            payload["categoryId"] = int(projectCategory)

        url = self._get_url("project")

        r = self._session.post(url, data=json.dumps(payload))
        r.raise_for_status()
        r_json = json_loads(r)
        return r_json

    def add_user(
        self,
        username: str,
        email: str,
        directoryId: int = 1,
        password: str = None,
        fullname: str = None,
        notify: bool = False,
        active: bool = True,
        ignore_existing: bool = False,
        application_keys: Optional[List] = None,
    ):
        """Create a new Jira user.

        Args:
            username (str): the username of the new user
            email (str): email address of the new user
            directoryId (int): The directory ID the new user should be a part of (Default: 1)
            password (Optional[str]): Optional, the password for the new user
            fullname (Optional[str]): Optional, the full name of the new user
            notify (bool): Whether or not to send a notification to the new user. (Default: False)
            active (bool): Whether or not to make the new user active upon creation. (Default: True)
            ignore_existing (bool): Whether or not to ignore and existing user. (Default: False)
            applicationKeys (Optional[list]): Keys of products user should have access to

        Raises:
            JIRAError:  If username already exists and `ignore_existing` has not been set to `True`.

        Returns:
            bool: Whether or not the user creation was successful.


        """
        if not fullname:
            fullname = username
        # TODO(ssbarnea): default the directoryID to the first directory in jira instead
        # of 1 which is the internal one.
        url = self._get_latest_url("user")

        # implementation based on
        # https://docs.atlassian.com/jira/REST/ondemand/#d2e5173
        x: Dict[str, Any] = OrderedDict()

        x["displayName"] = fullname
        x["emailAddress"] = email
        x["name"] = username
        if password:
            x["password"] = password
        if notify:
            x["notification"] = "True"
        if application_keys is not None:
            x["applicationKeys"] = application_keys

        payload = json.dumps(x)
        try:
            self._session.post(url, data=payload)
        except JIRAError as e:
            if e.response:
                err = e.response.json()["errors"]
                if (
                    "username" in err
                    and err["username"] == "A user with that username already exists."
                    and ignore_existing
                ):
                    return True
            raise e
        return True

    def add_user_to_group(
        self, username: str, group: str
    ) -> Union[bool, Dict[str, Any]]:
        """Add a user to an existing group.

        Args:
            username (str): Username that will be added to specified group.
            group (str): Group that the user will be added to.

        Returns:
            Union[bool,Dict[str,Any]]: json response from Jira server for success or a value that evaluates as False in case of failure.
        """
        url = self._get_latest_url("group/user")
        x = {"groupname": group}
        y = {"name": username}

        payload = json.dumps(y)

        r: Dict[str, Any] = json_loads(self._session.post(url, params=x, data=payload))
        if "name" not in r or r["name"] != group:
            return False
        else:
            return r

    def remove_user_from_group(self, username: str, groupname: str):
        """Remove a user from a group.

        Args:
            username (str): The user to remove from the group.
            groupname (str): The group that the user will be removed from.
        """
        url = self._get_latest_url("group/user")
        x = {"groupname": groupname, "username": username}

        self._session.delete(url, params=x)

        return True

    def role(self) -> List[Dict[str, Any]]:
        """Return Jira role information.

        Returns:
            List[Dict[str,Any]]: List of current user roles

        """
        # https://developer.atlassian.com/cloud/jira/platform/rest/v3/?utm_source=%2Fcloud%2Fjira%2Fplatform%2Frest%2F&utm_medium=302#api-rest-api-3-role-get

        url = self._get_latest_url("role")

        r = self._session.get(url)
        data: List[Dict[str, Any]] = json_loads(r)
        return data

    # Experimental
    # Experimental support for iDalko Grid, expect API to change as it's using private APIs currently
    # https://support.idalko.com/browse/IGRID-1017
    def get_igrid(self, issueid: str, customfield: str, schemeid: str):
        url = self.server_url + "/rest/idalko-igrid/1.0/datagrid/data"
        if str(customfield).isdigit():
            customfield = f"customfield_{customfield}"
        params = {
            "_issueId": issueid,
            "_fieldId": customfield,
            "_confSchemeId": schemeid,
        }
        r = self._session.get(url, headers=self._options["headers"], params=params)
        return json_loads(r)

    # Jira Agile specific methods (GreenHopper)
    """
    Define the functions that interact with GreenHopper.
    """

    @translate_resource_args
    def boards(
        self,
        startAt: int = 0,
        maxResults: int = 50,
        type: str = None,
        name: str = None,
        projectKeyOrID=None,
    ) -> ResultList[Board]:
        """Get a list of board resources.

        Args:
            startAt: The starting index of the returned boards. Base index: 0.
            maxResults: The maximum number of boards to return per page. Default: 50
            type: Filters results to boards of the specified type. Valid values: scrum, kanban.
            name: Filters results to boards that match or partially match the specified name.
            projectKeyOrID: Filters results to boards that match the specified project key or ID.

        Returns:
            ResultList[Board]

        When old GreenHopper private API is used, paging is not enabled and all parameters are ignored.
        """
        params = {}
        if type:
            params["type"] = type
        if name:
            params["name"] = name
        if projectKeyOrID:
            params["projectKeyOrId"] = projectKeyOrID

        if (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            # Old, private API did not support pagination, all records were present in response,
            #   and no parameters were supported.
            if startAt or maxResults or params:
                warnings.warn(
                    "Old private GreenHopper API is used, all parameters will be ignored.",
                    Warning,
                )

            r_json: Dict[str, Any] = self._get_json(
                "rapidviews/list", base=self.AGILE_BASE_URL
            )
            boards = [
                Board(self._options, self._session, raw_boards_json)
                for raw_boards_json in r_json["views"]
            ]
            return ResultList(boards, 0, len(boards), len(boards), True)
        else:
            return self._fetch_pages(
                Board,
                "values",
                "board",
                startAt,
                maxResults,
                params,
                base=self.AGILE_BASE_URL,
            )

    @translate_resource_args
    def sprints(
        self,
        board_id: int,
        extended: bool = False,
        startAt: int = 0,
        maxResults: int = 50,
        state: str = None,
    ) -> ResultList[Sprint]:
        """Get a list of sprint GreenHopperResources.

        Args:
            board_id (int): the board to get sprints from
            extended (bool): Used only by old GreenHopper API to fetch additional information like
              startDate, endDate, completeDate, much slower because it requires an additional requests for each sprint.
              New Jira Agile API always returns this information without a need for additional requests.
            startAt (int): the index of the first sprint to return (0 based)
            maxResults (int): the maximum number of sprints to return
            state (str): Filters results to sprints in specified states. Valid values: `future`, `active`, `closed`.
              You can define multiple states separated by commas

        Returns:
            ResultList[Sprint]: (content depends on API version, but always contains id, name, state, startDate and endDate)
            When old GreenHopper private API is used, paging is not enabled,
            and `startAt`, `maxResults` and `state` parameters are ignored.
        """
        params = {}
        if state:
            params["state"] = state

        if (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            r_json: Dict[str, Any] = self._get_json(
                "sprintquery/%s?includeHistoricSprints=true&includeFutureSprints=true"
                % board_id,
                base=self.AGILE_BASE_URL,
            )

            if params:
                warnings.warn(
                    "Old private GreenHopper API is used, parameters %s will be ignored."
                    % params,
                    Warning,
                )

            if extended:
                sprints = [
                    Sprint(
                        self._options,
                        self._session,
                        self.sprint_info("", raw_sprints_json["id"]),
                    )
                    for raw_sprints_json in r_json["sprints"]
                ]
            else:
                sprints = [
                    Sprint(self._options, self._session, raw_sprints_json)
                    for raw_sprints_json in r_json["sprints"]
                ]

            return ResultList(sprints, 0, len(sprints), len(sprints), True)
        else:
            return self._fetch_pages(
                Sprint,
                "values",
                f"board/{board_id}/sprint",
                startAt,
                maxResults,
                params,
                self.AGILE_BASE_URL,
            )

    def sprints_by_name(self, id, extended=False):
        sprints = {}
        for s in self.sprints(id, extended=extended):
            if s.name not in sprints:
                sprints[s.name] = s.raw
            else:
                raise Exception
        return sprints

    def update_sprint(self, id, name=None, startDate=None, endDate=None, state=None):
        payload = {}
        if name:
            payload["name"] = name
        if startDate:
            payload["startDate"] = startDate
        if endDate:
            payload["endDate"] = endDate
        if state:
            if (
                self._options["agile_rest_path"]
                == GreenHopperResource.GREENHOPPER_REST_PATH
            ):
                raise NotImplementedError(
                    "Public Jira API does not support state update"
                )
            payload["state"] = state

        url = self._get_url(f"sprint/{id}", base=self.AGILE_BASE_URL)
        r = self._session.put(url, data=json.dumps(payload))

        return json_loads(r)

    def incompletedIssuesEstimateSum(self, board_id: str, sprint_id: str):
        """Return the total incompleted points this sprint."""
        data: Dict[str, Any] = self._get_json(
            f"rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}",
            base=self.AGILE_BASE_URL,
        )
        return data["contents"]["incompletedIssuesEstimateSum"]["value"]

    def removed_issues(self, board_id: str, sprint_id: str):
        """Return the completed issues for the sprint."""
        r_json: Dict[str, Any] = self._get_json(
            f"rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}",
            base=self.AGILE_BASE_URL,
        )
        issues = [
            Issue(self._options, self._session, raw_issues_json)
            for raw_issues_json in r_json["contents"]["puntedIssues"]
        ]

        return issues

    def removedIssuesEstimateSum(self, board_id: str, sprint_id: str):
        """Return the total incompleted points this sprint."""
        data: Dict[str, Any] = self._get_json(
            f"rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}",
            base=self.AGILE_BASE_URL,
        )
        return data["contents"]["puntedIssuesEstimateSum"]["value"]

    # TODO(ssbarnea): remove sprint_info() method, sprint() method suit the convention more
    def sprint_info(self, board_id: str, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Return the information about a sprint.

        Args:
            board_id (str): the board retrieving issues from. Deprecated and ignored.
            sprint_id (str): the sprint retrieving issues from
        """
        sprint = Sprint(self._options, self._session)
        sprint.find(sprint_id)
        return sprint.raw

    def sprint(self, id: int) -> Sprint:
        """Return the information about a sprint.

        Args:
            sprint_id (int): the sprint retrieving issues from

        Returns:
            Sprint
        """
        sprint = Sprint(self._options, self._session)
        sprint.find(id)
        return sprint

    # TODO(ssbarnea): remove this as we do have Board.delete()
    def delete_board(self, id):
        """Delete an agile board."""
        board = Board(self._options, self._session, raw={"id": id})
        board.delete()

    def create_board(
        self,
        name: str,
        project_ids: Union[str, List[str]],
        preset: str = "scrum",
        location_type: str = "user",
        location_id: Optional[str] = None,
    ) -> Board:
        """Create a new board for the ``project_ids``.

        Args:
            name (str): name of the board
            project_ids (str): the projects to create the board in
            preset (str): What preset to use for this board, options: kanban, scrum, diy. (Default: scrum)
            location_type (str): the location type. Available in cloud. (Default: user)
            location_id (Optional[str]): the id of project that the board should be located under.
             Omit this for a 'user' location_type. Available in cloud.

        Returns:
            Board: The newly created board
        """
        if (
            self._options["agile_rest_path"]
            != GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            raise NotImplementedError(
                "Jira Agile Public API does not support this request"
            )

        payload: Dict[str, Any] = {}
        if isinstance(project_ids, str):
            ids = []
            for p in project_ids.split(","):
                ids.append(self.project(p).id)
            project_ids = ",".join(ids)
        if location_id is not None:
            location_id = self.project(location_id).id
        payload["name"] = name
        if isinstance(project_ids, str):
            project_ids = project_ids.split(",")  # type: ignore # re-use of variable
        payload["projectIds"] = project_ids
        payload["preset"] = preset
        if self._is_cloud:
            payload["locationType"] = location_type
            payload["locationId"] = location_id
        url = self._get_url("rapidview/create/presets", base=self.AGILE_BASE_URL)
        r = self._session.post(url, data=json.dumps(payload))

        raw_issue_json = json_loads(r)
        return Board(self._options, self._session, raw=raw_issue_json)

    def create_sprint(
        self,
        name: str,
        board_id: int,
        startDate: Optional[Any] = None,
        endDate: Optional[Any] = None,
    ) -> Sprint:
        """Create a new sprint for the ``board_id``.

        Args:
            name (str): Name of the sprint
            board_id (int): Which board the sprint should be assigned.
            startDate (Optional[Any]): Start date for the sprint.
            endDate (Optional[Any]): End date for the sprint.

        Returns:
            Sprint: The newly created Sprint
        """
        payload: Dict[str, Any] = {"name": name}
        if startDate:
            payload["startDate"] = startDate
        if endDate:
            payload["endDate"] = endDate

        raw_issue_json: Dict[str, Any]
        if (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            url = self._get_url(f"sprint/{board_id}", base=self.AGILE_BASE_URL)
            r = self._session.post(url)
            raw_issue_json = json_loads(r)
            """ now r contains something like:
            {
                  "id": 742,
                  "name": "Sprint 89",
                  "state": "FUTURE",
                  "linkedPagesCount": 0,
                  "startDate": "None",
                  "endDate": "None",
                  "completeDate": "None",
                  "remoteLinks": []
            }"""

            url = self._get_url(
                f"sprint/{raw_issue_json['id']}", base=self.AGILE_BASE_URL
            )
            r = self._session.put(url, data=json.dumps(payload))
            raw_issue_json = json_loads(r)
        else:
            url = self._get_url("sprint", base=self.AGILE_BASE_URL)
            payload["originBoardId"] = board_id
            r = self._session.post(url, data=json.dumps(payload))
            raw_issue_json = json_loads(r)

        return Sprint(self._options, self._session, raw=raw_issue_json)

    def add_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]) -> Response:
        """Add the issues in ``issue_keys`` to the ``sprint_id``.

        The sprint must be started but not completed.

        If a sprint was completed, then have to also edit the history of the
        issue so that it was added to the sprint before it was completed,
        preferably before it started. A completed sprint's issues also all have
        a resolution set before the completion date.

        If a sprint was not started, then have to edit the marker and copy the
        rank of each issue too.

        Args:
            sprint_id (int): the sprint to add issues to
            issue_keys (List[str]): the issues to add to the sprint

        Returns:
            Response
        """
        if self._options["agile_rest_path"] == GreenHopperResource.AGILE_BASE_REST_PATH:
            url = self._get_url(f"sprint/{sprint_id}/issue", base=self.AGILE_BASE_URL)
            payload = {"issues": issue_keys}
            try:
                return self._session.post(url, data=json.dumps(payload))
            except JIRAError as e:
                if e.status_code == 404:
                    warnings.warn(
                        "Status code 404 may mean, that too old Jira Agile version is installed."
                        " At least version 6.7.10 is required."
                    )
                raise
        elif (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            # In old, private API the function does not exist anymore and we need to use
            # issue.update() to perform this operation
            # Workaround based on https://answers.atlassian.com/questions/277651/jira-agile-rest-api-example

            sprint_field_id = self._get_sprint_field_id()

            data = {
                "idOrKeys": issue_keys,
                "customFieldId": sprint_field_id,
                "sprintId": sprint_id,
                "addToBacklog": False,
            }
            url = self._get_url("sprint/rank", base=self.AGILE_BASE_URL)
            return self._session.put(url, data=json.dumps(data))
        else:
            raise NotImplementedError(
                'No API for adding issues to sprint for agile_rest_path="%s"'
                % self._options["agile_rest_path"]
            )

    def add_issues_to_epic(
        self, epic_id: str, issue_keys: str, ignore_epics: bool = True
    ) -> Response:
        """Add the issues in ``issue_keys`` to the ``epic_id``.

        Args:
            epic_id (str): The ID for the epic where issues should be added.
            issue_keys (str): The issues to add to the epic
            ignore_epics (bool): ignore any issues listed in ``issue_keys`` that are epics. (Default: True)

        """
        if (
            self._options["agile_rest_path"]
            != GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            # TODO(ssbarnea): simulate functionality using issue.update()?
            raise NotImplementedError(
                "Jira Agile Public API does not support this request"
            )

        data: Dict[str, Any] = {}
        data["issueKeys"] = issue_keys
        data["ignoreEpics"] = ignore_epics
        url = self._get_url(f"epics/{epic_id}/add", base=self.AGILE_BASE_URL)
        return self._session.put(url, data=json.dumps(data))

    # TODO(ssbarnea): Both GreenHopper and new Jira Agile API support moving more than one issue.
    def rank(self, issue: str, next_issue: str) -> Response:
        """Rank an issue before another using the default Ranking field, the one named 'Rank'.

        Args:
            issue (str): issue key of the issue to be ranked before the second one.
            next_issue (str): issue key of the second issue.
        """
        if not self._rank:
            for field in self.fields():
                if field["name"] == "Rank":
                    if (
                        field["schema"]["custom"]
                        == "com.pyxis.greenhopper.jira:gh-lexo-rank"
                    ):
                        self._rank = field["schema"]["customId"]
                        break
                    elif (
                        field["schema"]["custom"]
                        == "com.pyxis.greenhopper.jira:gh-global-rank"
                    ):
                        # Obsolete since Jira v6.3.13.1
                        self._rank = field["schema"]["customId"]

        if self._options["agile_rest_path"] == GreenHopperResource.AGILE_BASE_REST_PATH:
            url = self._get_url("issue/rank", base=self.AGILE_BASE_URL)
            payload = {
                "issues": [issue],
                "rankBeforeIssue": next_issue,
                "rankCustomFieldId": self._rank,
            }
            try:
                return self._session.put(url, data=json.dumps(payload))
            except JIRAError as e:
                if e.status_code == 404:
                    warnings.warn(
                        "Status code 404 may mean, that too old Jira Agile version is installed."
                        " At least version 6.7.10 is required."
                    )
                raise
        elif (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            data = {
                "issueKeys": [issue],
                "rankBeforeKey": next_issue,
                "customFieldId": self._rank,
            }
            url = self._get_url("rank", base=self.AGILE_BASE_URL)
            return self._session.put(url, data=json.dumps(data))
        else:
            raise NotImplementedError(
                'No API for ranking issues for agile_rest_path="%s"'
                % self._options["agile_rest_path"]
            )

    def move_to_backlog(self, issue_keys: str) -> Response:
        """Move issues in ``issue_keys`` to the backlog, removing them from all sprints that have not been completed.

        Args:
            issue_keys (str): the issues to move to the backlog

        Raises:
            JIRAError: If moving issues to backlog fails
        """
        if self._options["agile_rest_path"] == GreenHopperResource.AGILE_BASE_REST_PATH:
            url = self._get_url("backlog/issue", base=self.AGILE_BASE_URL)
            payload = {"issues": issue_keys}
            try:
                return self._session.post(url, data=json.dumps(payload))
            except JIRAError as e:
                if e.status_code == 404:
                    warnings.warn(
                        "Status code 404 may mean, that too old Jira Agile version is installed."
                        " At least version 6.7.10 is required."
                    )
                raise
        elif (
            self._options["agile_rest_path"]
            == GreenHopperResource.GREENHOPPER_REST_PATH
        ):
            # In old, private API the function does not exist anymore and we need to use
            # issue.update() to perform this operation
            # Workaround based on https://answers.atlassian.com/questions/277651/jira-agile-rest-api-example

            sprint_field_id = self._get_sprint_field_id()

            data = {
                "idOrKeys": issue_keys,
                "customFieldId": sprint_field_id,
                "addToBacklog": True,
            }
            url = self._get_url("sprint/rank", base=self.AGILE_BASE_URL)
            return self._session.put(url, data=json.dumps(data))
        else:
            raise NotImplementedError(
                'No API for moving issues to backlog for agile_rest_path="%s"'
                % self._options["agile_rest_path"]
            )


class GreenHopper(JIRA):
    def __init__(self, options=None, basic_auth=None, oauth=None, async_=None):
        warnings.warn(
            "GreenHopper() class is deprecated, just use JIRA() instead.",
            DeprecationWarning,
        )
        JIRA.__init__(
            self, options=options, basic_auth=basic_auth, oauth=oauth, async_=async_
        )
