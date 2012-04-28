import unittest

from jira.client import JIRA

class JIRAIssueTests(unittest.TestCase):

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


def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item['key'] == key:
            return seq_item