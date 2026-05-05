from __future__ import annotations

from jira.resources import convert_display_name_to_python_name
from tests.conftest import JiraTestCase


class IssueDisplayNameFieldsTest(JiraTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_1_obj = self.test_manager.project_b_issue1_obj

    def test_issue_has_display_name_fields(self):
        issue = self.issue_1_obj
        all_attrs = [attr for attr in dir(issue.fields) if not attr.startswith('__')]
        custom_field_ids = [attr for attr in all_attrs if attr.startswith('customfield_')]

        self.assertGreater(len(custom_field_ids), 0)

        standard_fields = ['summary', 'status', 'priority', 'created']
        for field in standard_fields:
            self.assertIn(field, all_attrs)

        expected_minimum = len(custom_field_ids) + len(standard_fields)
        self.assertGreater(len(all_attrs), expected_minimum)

    def test_issue_field_access_patterns(self):
        issue = self.issue_1_obj

        self.assertIsNotNone(issue.fields.summary)
        self.assertIsNotNone(issue.fields.status)

        custom_fields = [attr for attr in dir(issue.fields) if attr.startswith('customfield_')]
        if custom_fields:
            getattr(issue.fields, custom_fields[0])

        all_fields = dir(issue.fields)
        self.assertIsInstance(all_fields, list)
        self.assertGreater(len(all_fields), 10)

    def test_issue_field_equivalence_real_data(self):
        issue = self.issue_1_obj

        if not hasattr(self.jira, '_fields_cache') or not self.jira._fields_cache:
            self.skipTest("JIRA instance doesn't have fields cache populated")

        fields_cache = self.jira._fields_cache
        tested_pairs = 0

        for display_name, field_id in fields_cache.items():
            if tested_pairs >= 3:
                break

            if hasattr(issue.fields, field_id):
                python_name = convert_display_name_to_python_name(display_name)

                if hasattr(issue.fields, python_name):
                    original_value = getattr(issue.fields, field_id)
                    display_value = getattr(issue.fields, python_name)
                    self.assertEqual(original_value, display_value)
                    tested_pairs += 1

        if tested_pairs == 0:
            self.skipTest("No suitable field pairs found for equivalence testing")

    def test_issue_custom_field_values_preserved(self):
        issue = self.issue_1_obj

        custom_fields_with_values = []
        for attr in dir(issue.fields):
            if attr.startswith('customfield_'):
                value = getattr(issue.fields, attr, None)
                if value is not None:
                    custom_fields_with_values.append((attr, value))

        self.assertGreater(len(custom_fields_with_values), 0)

        fields_cache = getattr(self.jira, '_fields_cache', {})

        for field_id, original_value in custom_fields_with_values[:3]:
            display_name = None
            for name, fid in fields_cache.items():
                if fid == field_id:
                    display_name = name
                    break

            if display_name:
                python_name = convert_display_name_to_python_name(display_name)

                if hasattr(issue.fields, python_name):
                    display_value = getattr(issue.fields, python_name)
                    self.assertIs(
                        original_value, display_value,
                        f"Values should be the same object: {field_id} vs {python_name}"
                    )

    def test_issue_fields_dir_includes_display_names(self):
        issue = self.issue_1_obj
        all_attrs = dir(issue.fields)

        standard_fields = ['summary', 'status', 'priority', 'issuetype']
        for field in standard_fields:
            self.assertIn(field, all_attrs)

        custom_field_ids = [attr for attr in all_attrs if attr.startswith('customfield_')]
        self.assertGreater(len(custom_field_ids), 0)

        standard_and_custom = set(standard_fields + custom_field_ids +
                                ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__',
                                 '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__',
                                 '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__',
                                 '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__',
                                 '__str__', '__subclasshook__', '__weakref__', '_issue_session',
                                 'aggregateprogress', 'aggregatetimeestimate', 'aggregatetimeoriginalestimate',
                                 'aggregatetimespent', 'archivedby', 'archiveddate', 'assignee', 'attachment',
                                 'comment', 'components', 'created', 'creator', 'description', 'duedate',
                                 'environment', 'fixVersions', 'issuelinks', 'labels', 'lastViewed',
                                 'progress', 'project', 'reporter', 'resolution', 'resolutiondate',
                                 'security', 'subtasks', 'timeestimate', 'timeoriginalestimate',
                                 'timespent', 'timetracking', 'updated', 'versions', 'votes',
                                 'watches', 'worklog', 'workratio'])

        display_name_fields = [attr for attr in all_attrs if attr not in standard_and_custom]
        self.assertGreater(len(display_name_fields), 0)

    def test_issue_creation_with_display_names(self):
        fresh_issue = self.jira.issue(self.issue_1)

        all_attrs = dir(fresh_issue.fields)
        custom_fields = [attr for attr in all_attrs if attr.startswith('customfield_')]

        expected_display_names = len(custom_fields) > 0

        if expected_display_names:
            standard_and_meta_fields = {
                '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__',
                '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__',
                '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__',
                '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__',
                '__str__', '__subclasshook__', '__weakref__', '_issue_session',
                'aggregateprogress', 'aggregatetimeestimate', 'aggregatetimeoriginalestimate',
                'aggregatetimespent', 'archivedby', 'archiveddate', 'assignee', 'attachment',
                'comment', 'components', 'created', 'creator', 'description', 'duedate',
                'environment', 'fixVersions', 'issuelinks', 'issuetype', 'labels', 'lastViewed',
                'priority', 'progress', 'project', 'reporter', 'resolution', 'resolutiondate',
                'security', 'status', 'subtasks', 'summary', 'timeestimate',
                'timeoriginalestimate', 'timespent', 'timetracking', 'updated',
                'versions', 'votes', 'watches', 'worklog', 'workratio'
            }

            potential_display_names = [
                attr for attr in all_attrs
                if attr not in standard_and_meta_fields and not attr.startswith('customfield_')
            ]

            self.assertGreater(len(potential_display_names), 0)


if __name__ == '__main__':
    import unittest
    unittest.main()
