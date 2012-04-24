class JIRAError(Exception):
    def __init__(self, url, status_code, msg):
        self.url = url
        self.status_code = status_code
        self.msg = msg