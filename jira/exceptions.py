# -*- coding: utf-8 -*-
import os
import tempfile

from requests import Response


class JIRAError(Exception):
    """General error raised for all problems in operation of the client."""

    log_to_tempfile = True
    if "GITHUB_ACTION" in os.environ:
        log_to_tempfile = False  # GitHub Actions is keeping only the console log.

    def __init__(
        self,
        text: str = None,
        status_code: int = None,
        url: str = None,
        request: Response = None,
        response: Response = None,
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
                details += f"\n\trequest headers = {self.request.headers}"

            if hasattr(self.request, "text"):
                details += f"\n\trequest text = {self.request.text}"
        if self.response is not None:
            if hasattr(self.response, "headers"):
                details += f"\n\tresponse headers = {self.response.headers}"

            if hasattr(self.response, "text"):
                details += f"\n\tresponse text = {self.response.text}"

        # separate logging for CI makes sense.
        if self.ci_run:
            if self.text:
                t += f"\n\ttext: {self.text}"
            t += details
        # Only log to tempfile if the option is set.
        elif self.log_to_tempfile:
            fd, file_name = tempfile.mkstemp(suffix=".tmp", prefix="jiraerror-")
            with open(file_name, "w") as f:
                t += f" details: {file_name}"
                f.write(details)
        # Otherwise, just return the error as usual
        else:
            if self.text:
                t += f"\n\ttext: {self.text}"
            t += f"\n\t{details}"

        return t
