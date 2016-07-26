import pytest
from time import sleep

from jira import JIRAError


def test_application_properties(jira_admin):
    props = jira_admin.application_properties()
    for p in props:
        assert isinstance(p, dict)
        assert set(p.keys()).issuperset(
            set(['type', 'name', 'value', 'key', 'id']))


def test_application_property(jira_admin):
    clone_prefix = jira_admin.application_properties(
        key='jira.lf.text.headingcolour')
    assert clone_prefix['value'] == '#292929'


def test_set_application_property(jira_admin):
    prop = 'jira.lf.favicon.hires.url'
    valid_value = '/jira-favicon-hires.png'
    invalid_value = '/Tjira-favicon-hires.png'
    counter = 0

    while jira_admin.application_properties(key=prop)['value'] != \
            valid_value and counter < 3:
        if counter:
            sleep(10)
        jira_admin.set_application_property(prop, invalid_value)
        assert jira_admin.application_properties(key=prop)['value'] == \
            invalid_value

        jira_admin.set_application_property(prop, valid_value)
        assert jira_admin.application_properties(key=prop)['value'] == \
            valid_value
        counter += 1


def test_setting_bad_property_raises(jira_admin):
    prop = 'random.nonexistent.property'
    with pytest.raises(JIRAError):
        jira_admin.set_application_property(prop, '666')
