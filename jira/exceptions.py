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
        if self.text:
            t += "\n\ttext: %s" % self.text
        if self.url:
            t += "\n\turl: %s" % self.url

        if self.request is not None and hasattr(self.request, 'headers'):
            t += "\n\trequest headers = %s" % self.request.headers

        if self.request is not None and hasattr(self.request, 'text'):
            t += "\n\trequest text = %s" % self.request.text

        if self.response is not None and hasattr(self.response, 'headers'):
            t += "\n\tresponse headers = %s" % self.response.headers

        if self.response is not None and hasattr(self.response, 'text'):
            t += "\n\tresponse text = %s" % self.response.text

        t += '\n'
        return t


