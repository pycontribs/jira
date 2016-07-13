import re
import pickle
import pytest
from tests import cls_for_resource
from jira import Role
from jira import Issue
from jira import Project
from jira.resources import Resource
from jira import JIRAError


def test_universal_find_existing_resource(test_manager, jira_admin):
    resource = jira_admin.find(
        'issue/{0}', test_manager.project_b_issue1)
    issue = jira_admin.issue(test_manager.project_b_issue1)

    assert resource.self == issue.self
    assert resource.key == issue.key


def test_find_invalid_resource_raises_exception(test_manager, jira_admin):
    with pytest.raises(JIRAError) as cm:
        jira_admin.find('woopsydoodle/{0}', '666')

    ex = cm.value
    # py26,27,34 gets 404 but on py33 gets 400
    assert ex.status_code in [400, 404]
    assert ex.text is not None
    assert re.search(
        '^https?://.*/rest/api/(2|latest)/woopsydoodle/666$', ex.url)


def test_pickling_resource(test_manager, jira_admin):
    resource = jira_admin.find(
        'issue/{0}', test_manager.project_b_issue1)

    pickled = pickle.dumps(resource.raw)
    unpickled = pickle.loads(pickled)
    cls = cls_for_resource(unpickled['self'])
    unpickled_instance = cls(jira_admin._options,
                             jira_admin._session, raw=pickle.loads(pickled))

    assert resource.key == unpickled_instance.key
    assert resource == unpickled_instance


def test_cls_for_resource():
    assert cls_for_resource(
        'https://jira.atlassian.com/rest/api/latest/issue/JRA-1330') == Issue
    assert cls_for_resource(
        'http://localhost:2990/jira/rest/api/latest/project/BULK') == Project
    assert cls_for_resource(
        'http://imaginary-jira.com/rest/api/latest/'
        'project/IMG/role/10002') == Role
    assert cls_for_resource(
        'http://customized-jira.com/rest/'
        'plugin-resource/4.5/json/getMyObject') == Resource
