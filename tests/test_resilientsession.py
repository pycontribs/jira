import logging

import jira.resilientsession
from tests.conftest import JiraTestCase


class ListLoggingHandler(logging.Handler):
    """A logging handler that records all events in a list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def reset(self):
        self.records = []


class ResilientSessionLoggingConfidentialityTests(JiraTestCase):
    """No sensitive data shall be written to the log."""

    def setUp(self):
        self.loggingHandler = ListLoggingHandler()
        jira.resilientsession.logging.getLogger().addHandler(self.loggingHandler)

    def test_logging_with_connection_error(self):
        """No sensitive data shall be written to the log in case of a connection error."""
        witness = "etwhpxbhfniqnbbjoqvw"  # random string; hopefully unique
        for max_retries in (0, 1):
            for verb in ("get", "post", "put", "delete", "head", "patch", "options"):
                with self.subTest(max_retries=max_retries, verb=verb):
                    with jira.resilientsession.ResilientSession() as session:
                        session.max_retries = max_retries
                        session.max_retry_delay = 0
                        try:
                            getattr(session, verb)(
                                "http://127.0.0.1:9",
                                headers={"sensitive_header": witness},
                                data={"sensitive_data": witness},
                            )
                        except jira.resilientsession.ConnectionError:
                            pass
                    # check that `witness` does not appear in log
                    for record in self.loggingHandler.records:
                        self.assertNotIn(witness, record.msg)
                        for arg in record.args:
                            self.assertNotIn(witness, str(arg))
                        self.assertNotIn(witness, str(record))
                    self.loggingHandler.reset()

    def tearDown(self):
        jira.resilientsession.logging.getLogger().removeHandler(self.loggingHandler)
        del self.loggingHandler
