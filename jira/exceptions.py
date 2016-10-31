import os
import tempfile


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
        if self.url:
            t += " url: %s" % self.url

        details = ""
        if self.request is not None and hasattr(self.request, 'headers'):
            details += "\n\trequest headers = %s" % self.request.headers

        if self.request is not None and hasattr(self.request, 'text'):
            details += "\n\trequest text = %s" % self.request.text

        if self.response is not None and hasattr(self.response, 'headers'):
            details += "\n\tresponse headers = %s" % self.response.headers

        if self.response is not None and hasattr(self.response, 'text'):
            details += "\n\tresponse text = %s" % self.response.text

        if self.text:
            t += "\n\ttext: %s" % self.text
            
        t += "\n\t" + details

        return t
