from __future__ import annotations

import copy
import pickle
import warnings

import pytest

import jira.client
import jira.resources
from tests.conftest import allow_on_cloud

pytestmark = pytest.mark.unit

MOCK_URL = "http://customized-jira.com/rest/"


def url_test_case(example_url: str):
    return f"{MOCK_URL}{example_url}"


class TestResource:
    # fmt: off
    @pytest.mark.parametrize(
        ["example_url", "expected_class"],
        [
            (url_test_case("api/latest/issue/JRA-1330"), jira.resources.Issue),
            (url_test_case("api/latest/project/BULK"), jira.resources.Project),
            (url_test_case("api/latest/project/IMG/role/10002"), jira.resources.Role),
            (url_test_case("plugin-resource/4.5/json/getMyObject"), jira.resources.UnknownResource),
            (url_test_case("group?groupname=bla"), jira.resources.Group),
            (url_test_case("user?username=bla"), jira.resources.User),  # Jira Server / Data Center
            (url_test_case("user?accountId=bla"), jira.resources.User),  # Jira Cloud
            (url_test_case("api/latest/dashboard/12345"), jira.resources.Dashboard),
            (url_test_case("api/latest/dashboard/1/items/1/properties"), jira.resources.DashboardItemPropertyKey),
            (url_test_case("api/latest/dashboard/1/items/1/properties/property"), jira.resources.DashboardItemProperty),
            (url_test_case("api/latest/dashboard/1/gadget/1"), jira.resources.DashboardGadget),
            (url_test_case("api/2/filter/10035"), jira.resources.Filter),
        ],
        ids=[
            "issue",
            "project",
            "role",
            "unknown_resource",
            "group",
            "user",
            "user_cloud",
            "dashboard",
            "dashboard_item_property_key",
            "dashboard_item_property",
            "dashboard_gadget",
            "filter",
        ],
    )
    # fmt: on
    @allow_on_cloud
    def test_cls_for_resource(self, example_url, expected_class):
        """Test the regex recognizes the right class for a given URL."""
        assert jira.resources.cls_for_resource(example_url) == expected_class


def test_resource_without_raw_has_no_attributes():
    resource = jira.resources.Resource("thing/{0}", {"server": "x"}, None)
    del resource.raw

    assert not hasattr(resource, "anything")
    copy.copy(resource)
    pickle.loads(pickle.dumps(resource))


def test_resource_without_raw_has_str_and_repr():
    resource = jira.resources.Resource("thing/{0}", {"server": "x"}, None)
    del resource.raw

    expected = f"<JIRA Resource at {id(resource)}>"
    assert repr(resource) == expected
    assert str(resource) == expected


def test_validate_with_malformed_session_response_does_not_recurse(requests_mock):
    requests_mock.get(
        "https://jira.example.net/rest/auth/1/session", json={"something": "blah"}
    )

    with pytest.raises(KeyError, match="self") as raised:
        jira.client.JIRA(
            "https://jira.example.net",
            token_auth="test-token",
            validate=True,
            get_server_info=False,
        )
    half_built_user = raised.traceback[-1].frame.f_locals["self"]
    assert not hasattr(half_built_user, "accountId")


XRAY_STEPS_RAW = {
    "fields": {
        "customfield_10004": {
            "steps": [
                {"index": 1, "fields": {"action": "Step 1", "expected result": "R1"}},
                {"index": 2, "fields": {"action": "Step 2", "expected result": "R2"}},
            ]
        }
    }
}


def test_dict2resource_aliases_spaced_keys_with_underscores():
    """Keys with spaces stay reachable by name and gain a dot-accessible alias (#1865)."""
    obj = jira.resources.dict2resource(copy.deepcopy(XRAY_STEPS_RAW))

    steps = obj.fields.customfield_10004.steps
    assert [step.fields.expected_result for step in steps] == ["R1", "R2"]
    assert [getattr(step.fields, "expected result") for step in steps] == ["R1", "R2"]


def test_dict2resource_alias_leaves_raw_unchanged():
    raw = copy.deepcopy(XRAY_STEPS_RAW)
    issue = jira.resources.Issue({"server": "x"}, None, raw)

    assert issue.raw == XRAY_STEPS_RAW
    step = issue.fields.customfield_10004.steps[0]
    assert step.fields.expected_result == "R1"


def test_dict2resource_keeps_keys_without_spaces_unchanged():
    obj = jira.resources.dict2resource({"action": "Step 1", "count": 3})

    assert vars(obj) == {"action": "Step 1", "count": 3}


@pytest.mark.parametrize("order", ["alias_first", "spaced_first"])
def test_dict2resource_alias_clashing_with_raw_key_warns(order):
    pairs = [("a_b", "underscored"), ("a b", "spaced")]
    raw = dict(pairs if order == "alias_first" else reversed(pairs))

    with pytest.warns(
        UserWarning, match="'a_b': it clashes with the existing key 'a_b'. Read 'a b'"
    ):
        obj = jira.resources.dict2resource(raw)

    assert obj.a_b == "underscored"
    assert getattr(obj, "a b") == "spaced"


def test_dict2resource_spaced_keys_sharing_an_alias_warn():
    raw = {"a b_c": 1, "a_b c": 2}

    with pytest.warns(UserWarning, match=r"'a_b_c'.*\['a b_c', 'a_b c'\]"):
        obj = jira.resources.dict2resource(raw)

    assert not hasattr(obj, "a_b_c")
    assert getattr(obj, "a b_c") == 1
    assert getattr(obj, "a_b c") == 2


def test_dict2resource_alias_does_not_shadow_class_attributes():
    raw = {"self": "http://x/rest/api/2/issue/1", "add field value": 1}

    with pytest.warns(UserWarning, match="'add_field_value': Issue already defines it"):
        issue = jira.resources.Issue({"server": "x"}, None, raw)

    assert callable(issue.add_field_value)
    assert getattr(issue, "add field value") == 1


@pytest.mark.parametrize("key", [" options", "1 st", "a-b c"])
def test_dict2resource_skips_alias_that_is_not_a_public_identifier(key):
    options = {"server": "x"}
    raw = {"self": "http://x/rest/api/2/issue/1", key: 1}

    without_key = jira.resources.Issue(options, None, {"self": raw["self"]})

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        issue = jira.resources.Issue(options, None, raw)

    assert getattr(issue, key) == 1
    assert issue._options is options
    assert vars(issue).keys() == vars(without_key).keys() | {key}
