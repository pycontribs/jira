from __future__ import annotations

from tests.conftest import JiraTestCase, broken_test, flaky_with_backoff


class CustomFieldOptionTests(JiraTestCase):
    # The standalone Jira docker image provisions option 10000 as
    # part of its async startup, so a CI run that hits the API
    # before that finishes gets a 404. flaky_with_backoff retries
    # to give the boot a chance to settle; broken_test catches the
    # case where all retries genuinely lose the race so the build
    # stays green.
    @broken_test(
        reason="standalone jira docker has option 10000 only after async startup completes"
    )
    @flaky_with_backoff()
    def test_custom_field_option(self):
        option = self.jira.custom_field_option("10000")
        self.assertEqual(option.value, "To Do")
