from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any

from requests import Response


def _sanitize_headers(headers: dict[str, Any] | Any) -> dict[str, Any] | Any:
    """Mask sensitive headers."""
    if not isinstance(headers, dict) and not hasattr(headers, "items"):
        return headers

    sensitive_headers = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-atlassian-token",
        "proxy-authorization",
    }
    sanitized = dict(headers)
    for key in sanitized:
        if key.lower() in sensitive_headers:
            sanitized[key] = "********"
    return sanitized


def _sanitize_body(body: str | Any) -> str | Any:
    """Mask sensitive information in the body (e.g. passwords in JSON)."""
    if not isinstance(body, str):
        return body

    try:
        data = json.loads(body)
        if isinstance(data, dict):
            sensitive_keys = {"password", "token", "secret", "access_token"}

            def scrub(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key.lower() in sensitive_keys:
                            obj[key] = "********"
                        else:
                            scrub(value)
                elif isinstance(obj, list):
                    for item in obj:
                        scrub(item)

            scrub(data)
            return json.dumps(data)
    except (json.JSONDecodeError, TypeError):
        # If it's not JSON, we can use some regex for common patterns if needed,
        # but JSON is the most common for Jira APIs.
        body = re.sub(r'("password"\s*:\s*")[^"]+(")', r'\1********\2', body, flags=re.I)
        body = re.sub(r'(password=[^&\s]+)', r'password=********', body, flags=re.I)

    return body


class JIRAError(Exception):
    """General error raised for all problems in operation of the client."""

    def __init__(
        self,
        text: str | None = None,
        status_code: int | None = None,
        url: str | None = None,
        request: Response | None = None,
        response: Response | None = None,
        **kwargs,
    ):
        """Creates a JIRAError.

        Args:
            text (Optional[str]): Message for the error.
            status_code (Optional[int]): Status code for the error.
            url (Optional[str]): Url related to the error.
            request (Optional[requests.Response]): Request made related to the error.
            response (Optional[requests.Response]): Response received related to the error.
            **kwargs: Will be used to get request headers.
        """
        self.status_code = status_code
        self.text = text
        self.url = url
        self.request = request
        self.response = response
        self.headers = kwargs.get("headers", None)
        self.log_to_tempfile = "PYJIRA_LOG_TO_TEMPFILE" in os.environ
        self.ci_run = "GITHUB_ACTION" in os.environ

    def __str__(self) -> str:
        t = f"JiraError HTTP {self.status_code}"
        if self.url:
            t += f" url: {self.url}"

        details = ""
        if self.request is not None:
            if hasattr(self.request, "headers"):
                details += f"\n\trequest headers = {_sanitize_headers(self.request.headers)}"

            if hasattr(self.request, "text"):
                details += f"\n\trequest text = {_sanitize_body(self.request.text)}"
        if self.response is not None:
            if hasattr(self.response, "headers"):
                details += f"\n\tresponse headers = {_sanitize_headers(self.response.headers)}"

            if hasattr(self.response, "text"):
                details += f"\n\tresponse text = {_sanitize_body(self.response.text)}"

        if self.log_to_tempfile:
            # Only log to tempfile if the option is set.
            _, file_name = tempfile.mkstemp(suffix=".tmp", prefix="jiraerror-")
            with open(file_name, "w") as f:
                t += f" details: {file_name}"
                f.write(details)
        else:
            # Otherwise, just return the error as usual
            if self.text:
                t += f"\n\ttext: {self.text}"
            t += f"\n\t{details}"

        return t


class NotJIRAInstanceError(Exception):
    """Raised in the case an object is not a JIRA instance."""

    def __init__(self, instance: Any):
        msg = (
            "The first argument of this function must be an instance of type "
            f"JIRA. Instance Type: {instance.__class__.__name__}"
        )
        super().__init__(msg)
