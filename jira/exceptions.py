import json

class JIRAError(Exception):
    """General error raised for all problems in operation of the client."""
    def __init__(self, status_code=None, text=None, url=None):
        self.status_code = status_code
        self.text = text
        self.url = url

    def __str__(self):
        if self.text:
            return 'HTTP {0}: "{1}"\n{2}'.format(self.status_code, self.text, self.url)
        else:
            return 'HTTP {0}: {1}'.format(self.status_code, self.url)

def raise_on_error(r):
    if r.status_code >= 400:
        error = json.loads(r.text)['errorMessages'][0]
        raise JIRAError(r.status_code, error, r.url)