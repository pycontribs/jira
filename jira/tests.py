import unittest

from jira.client import JIRA

class UniversalResourceTests(unittest.TestCase):
    pass

class ApplicationPropertiesTests(unittest.TestCase):

    def setUp(self):
        # this user has jira-system-administrators membership
        self.jira = JIRA(basic_auth=('eviladmin', 'eviladmin'))

    def test_application_properties(self):
        props = self.jira.application_properties()
        self.assertEqual(len(props), 12)

    def test_application_property(self):
        clone_prefix = self.jira.application_properties(key='jira.clone.prefix')
        self.assertEqual(clone_prefix['value'], 'CLONE -')

    def test_set_application_property(self):
        prop = 'jira.clone.prefix'
        self.jira.set_application_property(prop, 'TCLONE -')
        self.assertEqual(self.jira.application_properties(key=prop)['value'], 'TCLONE -')
        self.jira.set_application_property(prop, 'CLONE -')
        self.assertEqual(self.jira.application_properties(key=prop)['value'], 'CLONE -')

class AttachmentTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_attachment(self):
        attachment = self.jira.attachment('10030')
        self.assertEqual(attachment.filename, 'AdditionalPylons.jpg')
        self.assertEqual(attachment.size, 110787)

    def test_attachment_meta(self):
        meta = self.jira.attachment_meta()
        self.assertTrue(meta['enabled'])
        self.assertEqual(meta['uploadLimit'], 10485760)


class ComponentTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_component(self):
        component = self.jira.component('10003')
        self.assertEqual(component.name, 'Bacon')

    def test_component_count_related_issues(self):
        issue_count = self.jira.component_count_related_issues('10002')
        self.assertEqual(issue_count, 9)


class CustomFieldOptionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_custom_field_option(self):
        option = self.jira.custom_field_option('10010')
        self.assertEqual(option.value, 'Mehemet')


class DashboardTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('eviladmin', 'eviladmin'))

    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertEqual(len(dashboards.dashboards), 3)

    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter='my')
        self.assertEqual(len(dashboards.dashboards), 1)
        self.assertEqual(dashboards.dashboards[0].id, '10031')

    def test_dashboards_startAt(self):
        dashboards = self.jira.dashboards(startAt=2, maxResults=2)
        self.assertEqual(len(dashboards.dashboards), 1)

    def test_dashboards_maxResults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards.dashboards), 1)

    def test_dashboard(self):
        dashboard = self.jira.dashboard('10031')
        self.assertEqual(dashboard.id, '10031')
        self.assertEqual(dashboard.name, 'Evil\'O\'Administrator\'s "Funny DB"')


class FieldsTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_fields(self):
        fields = self.jira.fields()
        self.assertEqual(len(fields), 65)


class FilterTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_filter(self):
        filter = self.jira.filter('10016')
        self.assertEqual(filter.name, 'Bugs')
        self.assertEqual(filter.owner.name, 'admin')

    def test_favourite_filters(self):
        filters = self.jira.favourite_filters()
        self.assertEqual(len(filters), 1)


class GroupsTest(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_groups(self):
        groups = self.jira.groups()
        self.assertEqual(groups['total'], 7)

    def test_groups_with_query(self):
        groups = self.jira.groups('jira-')
        self.assertEqual(groups['total'], 4)

    def test_groups_with_exclude(self):
        groups = self.jira.groups('jira-', exclude='jira-system-administrators')
        self.assertEqual(groups['total'], 3)

class IssueTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_issue(self):
        issue = self.jira.issue('BULK-1')
        self.assertEqual(issue.key, 'BULK-1')
        self.assertEqual(issue.fields.summary, 'Version 2.0 Bacon issue')

    def test_issue_field_limiting(self):
        issue = self.jira.issue('BULK-2', fields='summary,comment')
        self.assertEqual(issue.fields.summary, 'Version 1.1.1 cheese issue')
        self.assertEqual(issue.fields.comment.total, 4)
        self.assertFalse(hasattr(issue.fields, 'reporter'))
        self.assertFalse(hasattr(issue.fields, 'progress'))

    def test_issue_expandos(self):
        issue = self.jira.issue('BULK-3', expand=('editmeta', 'schema'))
        self.assertTrue(hasattr(issue, 'editmeta'))
        self.assertTrue(hasattr(issue, 'schema'))
        self.assertFalse(hasattr(issue, 'changelog'))

    def test_createmeta(self):
        meta = self.jira.createmeta()
        self.assertEqual(len(meta['projects']), 12)
        xss_proj = find_by_key(meta['projects'], 'XSS')
        self.assertEqual(len(xss_proj['issuetypes']), 12)

    def test_createmeta_filter_by_name(self):
        meta = self.jira.createmeta(projectKeys=('BULK', 'XSS'), issuetypeNames='Improvement')
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertTrue(len(project['issuetypes']), 1)

    def test_createmeta_filter_by_id(self):
        meta = self.jira.createmeta(projectIds=('10001', '10040'), issuetypeIds=('3', '4', '5'))
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertTrue(len(project['issuetypes']), 3)

    def test_createmeta_expando(self):
        # limit to SCR project so the call returns promptly
        meta = self.jira.createmeta(projectKeys=('SCR'), expand=('projects.issuetypes.fields'))
        self.assertTrue('fields' in meta['projects'][0]['issuetypes'][0])

    def test_assign_issue(self):
        self.assertIsNone(self.jira.assign_issue('BULK-1', 'eviladmin'))
        self.assertEqual(self.jira.issue('BULK-1').fields.assignee.name, 'eviladmin')
        self.assertIsNone(self.jira.assign_issue('BULK-1', 'admin'))
        self.assertEqual(self.jira.issue('BULK-1').fields.assignee.name, 'admin')

    def test_comments(self):
        comments = self.jira.comments('BULK-1')
        self.assertEqual(len(comments), 29)
        comments = self.jira.comments('BULK-2')
        self.assertEqual(len(comments), 4)

    def test_comment(self):
        comment = self.jira.comment('BULK-1', '10072')
        self.assertTrue(comment.body.startswith('Mr. Bennet was so odd a mixture of quick parts'))

    def test_editmeta(self):
        meta = self.jira.editmeta('BULK-1')
        self.assertEqual(len(meta['fields']), 38)
        self.assertTrue('customfield_10642' in meta['fields'])
        self.assertTrue('customfield_10240' in meta['fields'])

    def test_remote_links(self):
        pass

    def test_remote_link(self):
        pass

    def test_transitions(self):
        transitions = self.jira.transitions('BULK-2')
        self.assertEqual(len(transitions), 2)

    def test_transition(self):
        transition = self.jira.transitions('BULK-2', '701')
        self.assertEqual(transition[0]['name'], 'Close Issue')

    def test_transition_expand(self):
        transition = self.jira.transitions('BULK-2', '701', expand=('transitions.fields'))
        self.assertTrue('fields' in transition[0])

    @unittest.skip('test data doesn\'t support voting')
    def test_votes(self):
        votes = self.jira.votes('BULK-1')
        self.assertEqual(votes.votes, 5)

    @unittest.skip('test data doesn\'t support watching')
    def test_watchers(self):
        watchers = self.jira.watchers('BULK-1')
        self.assertEqual(watchers.watchCount, 18)

    def test_worklogs(self):
        worklogs = self.jira.worklogs('BULK-1')
        self.assertEqual(len(worklogs), 6)

    def test_worklog(self):
        worklog = self.jira.worklog('BULK-1', '10045')
        self.assertEqual(worklog.author.name, 'admin')
        self.assertEqual(worklog.timeSpent, '4d')


class IssueLinkTests(unittest.TestCase):
    pass

def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item['key'] == key:
            return seq_item