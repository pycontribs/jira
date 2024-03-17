from __future__ import annotations

import os
from unittest import mock

import pytest

from jira.exceptions import JIRAError
from tests.conftest import JiraTestCase, allow_on_cloud, broken_test, rndstr


class DashboardTests(JiraTestCase):
    def setUp(self):
        super().setUp()
        self.dashboards_to_delete = []
        self.gadget_title = "Filter Results"
        self.dashboard_item_expected_key = "config"
        self.dashboard_item_column_names = "issuetype|issuekey|summary|priority|status"
        self.dashboard_item_num = 5
        self.dashboard_item_refresh = 15
        self.filter = self.jira.create_filter(
            rndstr(), "description", f"project={self.project_b}", True
        )

    def tearDown(self):
        for dashboard in self.dashboards_to_delete:
            dashboard.delete()
        super().tearDown()

    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertGreaterEqual(len(dashboards), 1)

    @broken_test(
        reason="standalone jira docker image has only 1 system dashboard by default"
    )
    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter="my")
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, "10101")

    def test_dashboards_startat(self):
        dashboards = self.jira.dashboards(startAt=0, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxresults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        expected_ds = self.jira.dashboards()[0]
        dashboard = self.jira.dashboard(expected_ds.id)
        self.assertEqual(dashboard.id, expected_ds.id)
        self.assertEqual(dashboard.name, expected_ds.name)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_create_dashboard(self):
        name = rndstr()
        description = rndstr()
        share_permissions = [{"type": "authenticated"}]

        dashboard = self.jira.create_dashboard(
            name=name, description=description, share_permissions=share_permissions
        )
        self.dashboards_to_delete.append(dashboard)

        self.assertEqual(dashboard.name, name)
        self.assertEqual(dashboard.description, description)
        # NOTE(jpavlav): This is a bit obtuse, but Jira mutates the type on this
        # object after the fact. `authenticated` corresponds to `loggedin`.
        self.assertEqual(dashboard.sharePermissions[0].type, "loggedin")

        # NOTE(jpavlav): The system dashboard always has the ID `10000`, just
        # ensuring we actually have a
        self.assertGreater(int(dashboard.id), 10000)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_update_dashboard(self):
        updated_name = "changed"
        name = rndstr()
        description = rndstr()
        share_permissions = [{"type": "authenticated"}]

        dashboard = self.jira.create_dashboard(
            name=name, description=description, share_permissions=share_permissions
        )
        self.dashboards_to_delete.append(dashboard)

        dashboard.update(name=updated_name)
        self.assertEqual(dashboard.name, updated_name)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_delete_dashboard(self):
        dashboard = self.jira.create_dashboard(name="to_delete")
        dashboard_id = dashboard.id
        delete_response = dashboard.delete()
        self.assertEqual(delete_response.status_code, 204)

        with pytest.raises(JIRAError) as ex:
            self.jira.dashboard(dashboard_id)

        self.assertEqual(ex.value.status_code, 404)
        self.assertEqual(
            ex.value.text, f"The dashboard with id '{dashboard_id}' does not exist."
        )

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_copy_dashboard(self):
        original_dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(original_dashboard)
        # NOTE(jpavlav): Add something to the dashboard so we can test the copy worked
        # as intended.
        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )

        original_gadget = self.jira.add_gadget_to_dashboard(
            original_dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )
        original_dashboard = self.jira.dashboard(original_dashboard.id)

        copied_dashboard = self.jira.copy_dashboard(
            original_dashboard.id, name=rndstr()
        )
        copied_dashboard = self.jira.dashboard(copied_dashboard.id)
        self.dashboards_to_delete.append(copied_dashboard)

        self.assertEqual(len(original_dashboard.gadgets), len(copied_dashboard.gadgets))
        self.assertEqual(original_gadget.color, copied_dashboard.gadgets[0].color)
        self.assertEqual(original_gadget.uri, copied_dashboard.gadgets[0].uri)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_all_dashboard_gadgets(self):
        # NOTE(jpalmer): This is a super basic test. We can't really rely on the fact
        # that the gadgets available at any given moment will be specifically represented
        # here and it would be silly to have to update the tests to adjust for that if
        # the starting list ever changed.
        gadgets = self.jira.all_dashboard_gadgets()
        self.assertGreater(len(gadgets), 0)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_dashboard_gadgets(self):
        gadget_count = 3
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)

        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        for _ in range(0, gadget_count):
            self.jira.add_gadget_to_dashboard(
                dashboard.id,
                color="blue",
                ignore_uri_and_module_key_validation=True,
                uri=filter_gadget.uri,
            )

        dashboard_gadgets = self.jira.dashboard_gadgets(dashboard.id)
        self.assertEqual(len(dashboard_gadgets), gadget_count)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_update_dashboard_automatic_refresh_minutes(self):
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)
        response = self.jira.update_dashboard_automatic_refresh_minutes(
            dashboard.id, 10
        )
        self.assertEqual(response.status_code, 204)
        response = self.jira.update_dashboard_automatic_refresh_minutes(dashboard.id, 0)
        self.assertEqual(response.status_code, 204)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_add_gadget_to_dashboard(self):
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)

        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        gadget = self.jira.add_gadget_to_dashboard(
            dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )

        dashboard = self.jira.dashboard(dashboard.id)
        self.assertEqual(dashboard.gadgets[0], gadget)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_remove_gadget_from_dashboard(self):
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)

        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        gadget = self.jira.add_gadget_to_dashboard(
            dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )

        dashboard = self.jira.dashboard(dashboard.id)
        self.assertEqual(len(dashboard.gadgets), 1)
        self.assertEqual(dashboard.gadgets[0], gadget)

        gadget.delete(dashboard.id)
        dashboard = self.jira.dashboard(dashboard.id)
        self.assertEqual(len(dashboard.gadgets), 0)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_update_gadget(self):
        new_color = "green"
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)
        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        gadget = self.jira.add_gadget_to_dashboard(
            dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )

        gadget = gadget.update(dashboard.id, color=new_color)
        self.assertEqual(gadget.color, new_color)
        self.assertEqual(gadget.raw["color"], new_color)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_dashboard_item_property_keys(self):
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)

        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        gadget = self.jira.add_gadget_to_dashboard(
            dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )

        dashboard_item_property_keys = self.jira.dashboard_item_property_keys(
            dashboard.id, gadget.id
        )
        self.assertEqual(len(dashboard_item_property_keys), 0)

        item_property_payload = {
            "filterId": self.filter.id,
            "columnNames": self.dashboard_item_column_names,
            "num": self.dashboard_item_num,
            "refresh": self.dashboard_item_refresh,
        }
        self.jira.set_dashboard_item_property(
            dashboard.id,
            gadget.id,
            self.dashboard_item_expected_key,
            value=item_property_payload,
        )

        dashboard_item_property_keys = self.jira.dashboard_item_property_keys(
            dashboard.id, gadget.id
        )
        self.assertEqual(len(dashboard_item_property_keys), 1)
        self.assertEqual(
            dashboard_item_property_keys[0].key, self.dashboard_item_expected_key
        )

        delete_response = dashboard_item_property_keys[0].delete()
        self.assertEqual(delete_response.status_code, 204)

        dashboard_item_property_keys = self.jira.dashboard_item_property_keys(
            dashboard.id, gadget.id
        )
        self.assertEqual(len(dashboard_item_property_keys), 0)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    def test_dashboard_item_properties(self):
        dashboard = self.jira.create_dashboard(
            name=rndstr(), share_permissions=[{"type": "authenticated"}]
        )
        self.dashboards_to_delete.append(dashboard)

        available_gadgets = self.jira.all_dashboard_gadgets()
        filter_gadget = next(
            gadget for gadget in available_gadgets if gadget.title == self.gadget_title
        )
        gadget = self.jira.add_gadget_to_dashboard(
            dashboard.id,
            color="blue",
            ignore_uri_and_module_key_validation=True,
            uri=filter_gadget.uri,
        )

        item_property_payload = {
            "filterId": self.filter.id,
            "columnNames": self.dashboard_item_column_names,
            "num": self.dashboard_item_num,
            "refresh": self.dashboard_item_refresh,
        }
        dashboard_item_property = self.jira.set_dashboard_item_property(
            dashboard.id,
            gadget.id,
            self.dashboard_item_expected_key,
            value=item_property_payload,
        )

        dashboard = self.jira.dashboard(dashboard.id)
        self.assertEqual(
            dashboard.gadgets[0].item_properties[0], dashboard_item_property
        )

        updated_item_property_payload = {"num": 10}
        updated_dashboard_item_property = dashboard_item_property.update(
            dashboard.id, gadget.id, value=updated_item_property_payload
        )
        self.assertEqual(
            updated_dashboard_item_property.value.num,
            updated_item_property_payload["num"],
        )

        delete_response = updated_dashboard_item_property.delete(
            dashboard.id, gadget.id
        )
        self.assertEqual(delete_response.status_code, 204)

    @pytest.mark.skipif(
        os.environ.get("CI_JIRA_TYPE", "Server").upper() != "CLOUD",
        reason="Functionality only available on Jira Cloud",
    )
    @allow_on_cloud
    @mock.patch("requests.Session.request")
    def test_set_dashboard_item_property_not_201_response(self, mocked_request):
        mocked_request.return_value = mock.MagicMock(ok=False, status_code=404)
        with pytest.raises(JIRAError) as ex:
            self.jira.set_dashboard_item_property(
                "id", "item_id", "config", {"this": "that"}
            )

        assert ex.value.status_code == 404
