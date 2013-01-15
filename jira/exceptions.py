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
        error = ''
        if r.text:
            try:
                response = json.loads(r.text)
                if 'message' in response:
                    # JIRA 5.1 errors
                    error = response['message']
                elif 'errorMessages' in response:
                    # JIRA 5.0.x error messages sometimes come wrapped in this array
                    errorMessages = response['errorMessages']
                    if isinstance(errorMessages, (list, tuple)) and len(errorMessages) > 0:
                        error = errorMessages[0]
                    else:
                        error = errorMessages
                else:
                    error = r.text
            except ValueError:
                error = r.text
        raise JIRAError(r.status_code, error, r.url)
