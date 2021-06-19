import unittest

from flaky import flaky

from jira.resources import (
    Group,
    Issue,
    Project,
    Role,
    UnknownResource,
    cls_for_resource,
)


@flaky
class ResourceTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_cls_for_resource(self):
        self.assertEqual(
            cls_for_resource(
                "https://jira.atlassian.com/rest/\
                api/latest/issue/JRA-1330"
            ),
            Issue,
        )
        self.assertEqual(
            cls_for_resource(
                "http://localhost:2990/jira/rest/\
                api/latest/project/BULK"
            ),
            Project,
        )
        self.assertEqual(
            cls_for_resource(
                "http://imaginary-jira.com/rest/\
                api/latest/project/IMG/role/10002"
            ),
            Role,
        )
        self.assertEqual(
            cls_for_resource(
                "http://customized-jira.com/rest/\
                plugin-resource/4.5/json/getMyObject"
            ),
            UnknownResource,
        )
        self.assertEqual(
            cls_for_resource(
                "http://customized-jira.com/rest/\
                group?groupname=bla"
            ),
            Group,
        )
