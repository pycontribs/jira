from __future__ import annotations

import logging
from time import sleep

import pytest

from tests.conftest import jira_svcTestCase, broken_test

LOGGER = logging.getLogger(__name__)


class jira_svcServiceDeskTests(jira_svcTestCase):
    def setUp(self):
        jira_svcTestCase.setUp(self)
        if not self.jira_svc.supports_service_desk():
            pytest.skip("Skipping Service Desk not enabled")

        try:
            self.jira_svc.delete_project(self.test_manager.project_sd)
        except Exception:
            LOGGER.warning("Failed to delete %s", self.test_manager.project_sd)

    @broken_test(reason="Broken needs fixing")
    def test_create_customer_request(self):
        self.jira_svc.create_project(
            key=self.test_manager.project_sd,
            name=self.test_manager.project_sd_name,
            ptype="service_desk",
            template_name="IT Service Desk",
        )
        service_desks = []
        for _ in range(3):
            service_desks = self.jira_svc.service_desks()
            if service_desks:
                break
            logging.warning("Service desk not reported...")
            sleep(2)
        self.assertTrue(service_desks, "No service desks were found!")
        service_desk = service_desks[0]

        for _ in range(3):
            request_types = self.jira_svc.request_types(service_desk)
            if request_types:
                logging.warning("Service desk request_types not reported...")
                break
            sleep(2)
        self.assertTrue(request_types, "No request_types for service desk found!")

        request = self.jira_svc.create_customer_request(
            dict(
                serviceDeskId=service_desk.id,
                requestTypeId=int(request_types[0].id),
                requestFieldValues=dict(
                    summary="Ticket title here", description="Ticket body here"
                ),
            )
        )

        self.assertEqual(request.fields.summary, "Ticket title here")
        self.assertEqual(request.fields.description, "Ticket body here")
