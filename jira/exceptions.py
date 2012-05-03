class JIRAError(Exception):
    """General error raised for all problems in operation of the client."""
    def __init__(self, reason, status_code=None, url=None):
        self.reason = reason
        self.status_code = status_code
        self.url = url

    def __str__(self):
        return self.reason
