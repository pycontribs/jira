import unittest
import re
import os

from jira.client import JIRA
from jira.exceptions import JIRAError
from jira.resources import Resource, cls_for_resource, Issue, Project, Role

TEST_ICON_PATH = '../resources/test/icon.png'

class UniversalResourceTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_universal_find_existing_resource(self):
        resource = self.jira.find('issue/{0}', 'BULK-1')
        issue = self.jira.issue('BULK-1')
        self.assertEqual(resource.self, issue.self)
        self.assertEqual(resource.key, issue.key)

    def test_universal_find_custom_resource(self):
        resource = Resource('nope/{0}', self.jira._options, None)  # don't need an actual session
        self.assertEqual('http://localhost:2990/jira/rest/api/2/nope/666', resource._url(('666',)))

    def test_find_invalid_resource_raises_exception(self):
        with self.assertRaises(JIRAError) as cm:
            self.jira.find('woopsydoodle/{0}', '666')

        ex = cm.exception
        self.assertEqual(ex.status_code, 404)
        self.assertRegexpMatches(ex.reason, r'Resource')
        self.assertEqual(ex.url, 'http://localhost:2990/jira/rest/api/2/woopsydoodle/666')

    def test_verify_works_with_https(self):
        self.jira = JIRA(options={'server': 'https://jira.atlassian.com'})

    def test_verify_fails_without_https(self):
        # we need a server that doesn't do https
        self.jira = JIRA(options={'server': 'https://www.yahoo.com'})
        self.assertRaises(JIRAError, self.jira.issue, 'BULK-1')


class ResourceTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_cls_for_resource(self):
        self.assertEqual(cls_for_resource('https://jira.atlassian.com/rest/api/2/issue/JRA-1330'), Issue)
        self.assertEqual(cls_for_resource('http://localhost:2990/jira/rest/api/2/project/BULK'), Project)
        self.assertEqual(cls_for_resource('http://imaginary-jira.com/rest/api/2/project/IMG/role/10002'), Role)
        self.assertEqual(cls_for_resource('http://customized-jira.com/rest/plugin-resource/4.5/json/getMyObject'), Resource)


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

    def test_setting_bad_property_raises(self):
        prop = 'random.nonexistent.property'
        self.assertRaises(JIRAError, self.jira.set_application_property, prop, '666')


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

    def test_create_component(self):
        component = self.jira.create_component('Test Component', 'BULK', description='testing!!', leadUserName='fred',
                assigneeType='PROJECT_LEAD', isAssigneeTypeValid=False)
        self.assertEqual(component.name, 'Test Component')
        self.assertEqual(component.description, 'testing!!')
        self.assertEqual(component.lead.name, 'fred')
        self.assertEqual(component.assigneeType, 'PROJECT_LEAD')
        self.assertTrue(component.isAssigneeTypeValid)

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
        self.assertEqual(len(fields), 63)


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

    def test_create_issue_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': 'BULK'}, summary='Test issue created',
                description='blahery', issuetype={'name': 'Bug'}, customfield_10540={'key': 'XSS'})
        self.assertEqual(issue.fields.summary, 'Test issue created')
        self.assertEqual(issue.fields.description, 'blahery')
        self.assertEqual(issue.fields.issuetype.name, 'Bug')
        self.assertEqual(issue.fields.project.key, 'BULK')
        self.assertEqual(issue.fields.customfield_10540.key, 'XSS')

    def test_create_issue_with_fielddict(self):
        fields = {
            'project': {
                'key': 'BULK'
            },
            'summary': 'Issue created from field dict',
            'description': "Microphone #1, is not this a lot of fun",
            'issuetype': {
                'name': 'Task'
            },
            'customfield_10540': {
                'key': 'DOC'
            },
            'priority': {
                'name': 'Critical'
            }
        }
        issue = self.jira.create_issue(fields=fields)
        self.assertEqual(issue.fields.summary, 'Issue created from field dict')
        self.assertEqual(issue.fields.description, "Microphone #1, is not this a lot of fun")
        self.assertEqual(issue.fields.issuetype.name, 'Task')
        self.assertEqual(issue.fields.project.key, 'BULK')
        self.assertEqual(issue.fields.customfield_10540.key, 'DOC')
        self.assertEqual(issue.fields.priority.name, 'Critical')

    def test_create_issue_without_prefetch(self):
        issue = self.jira.create_issue(prefetch=False, project={'key': 'BULK'}, summary='Test issue created',
            description='blahery', issuetype={'name': 'Bug'}, customfield_10540={'key': 'XSS'})
        self.assertTrue(hasattr(issue, 'self'))
        self.assertFalse(hasattr(issue, 'fields'))

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

    def test_assign_to_bad_issue_raises(self):
        self.assertRaises(JIRAError, self.jira.assign_issue, 'NOPE-1', 'notauser')

    def test_comments(self):
        comments = self.jira.comments('BULK-1')
        self.assertEqual(len(comments), 29)
        comments = self.jira.comments('BULK-2')
        self.assertEqual(len(comments), 4)

    def test_comment(self):
        comment = self.jira.comment('BULK-1', '10072')
        self.assertTrue(comment.body.startswith('Mr. Bennet was so odd a mixture of quick parts'))

    def test_add_comment(self):
        comment = self.jira.add_comment('BULK-3', 'a test comment!',
                visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'a test comment!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')

    def test_editmeta(self):
        meta = self.jira.editmeta('BULK-1')
        self.assertEqual(len(meta['fields']), 38)
        self.assertTrue('customfield_10642' in meta['fields'])
        self.assertTrue('customfield_10240' in meta['fields'])

    def test_remote_links(self):
        links = self.jira.remote_links('QA-44')
        self.assertEqual(len(links), 1)
        links = self.jira.remote_links('BULK-1')
        self.assertEqual(len(links), 0)

    def test_remote_link(self):
        link = self.jira.remote_link('QA-44', '10000')
        self.assertEqual(link.id, 10000)
        self.assertTrue(hasattr(link, 'globalId'))
        self.assertTrue(hasattr(link, 'relationship'))

    def test_add_remote_link(self):
        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
                object={'url': 'http://google.com', 'title': 'googlicious!'},
                application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
        # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
        link = self.jira.remote_link('BULK-3', link.id)
        self.assertEqual(link.application.name, 'far too silly')
        self.assertEqual(link.application.type, 'sketch')
        self.assertEqual(link.object.url, 'http://google.com')
        self.assertEqual(link.object.title, 'googlicious!')
        self.assertEqual(link.relationship, 'mousebending')
        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')

    def test_transitions(self):
        transitions = self.jira.transitions('BULK-2')
        self.assertEqual(len(transitions), 2)

    def test_transition(self):
        transition = self.jira.transitions('BULK-2', '701')
        self.assertEqual(transition[0]['name'], 'Close Issue')

    def test_transition_expand(self):
        transition = self.jira.transitions('BULK-2', '701', expand=('transitions.fields'))
        self.assertTrue('fields' in transition[0])

    def test_transition_issue_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': 'BULK'}, summary='Test issue for transition created',
            description='blahery', issuetype={'name': 'Bug'}, customfield_10540={'key': 'XSS'})
        self.jira.transition_issue(issue.key, '2', assignee={'name': 'fred'})
        issue = self.jira.issue(issue.key)
        self.assertEqual(issue.fields.assignee.name, 'fred')
        self.assertEqual(issue.fields.status.id, '6')    # issue now 'Closed'

    def test_transition_issue_with_fielddict(self):
        issue = self.jira.create_issue(project={'key': 'BULK'}, summary='Test issue for transition created',
            description='blahery', issuetype={'name': 'Bug'}, customfield_10540={'key': 'XSS'})
        fields = {
            'assignee': {
                'name': 'fred'
            }
        }
        self.jira.transition_issue(issue.key, '5', fields=fields)
        issue = self.jira.issue(issue.key)
        self.assertEqual(issue.fields.assignee.name, 'fred')
        self.assertEqual(issue.fields.status.id, '5')    # issue now 'Resolved'

    @unittest.skip('test data doesn\'t support voting')
    def test_votes(self):
        votes = self.jira.votes('BULK-1')
        self.assertEqual(votes.votes, 5)

    @unittest.skip('test data doesn\'t support voting')
    def test_add_vote(self):
        votes = self.jira.votes('QA-44')
        self.assertEqual(votes.votes, 0)
        self.jira.add_vote('QA-44')
        votes = self.jira.votes('QA-44')
        self.assertEqual(votes.votes, 1)

    @unittest.skip('test data doesn\'t support voting')
    def test_remove_vote(self):
        votes = self.jira.votes('QA-44')
        self.assertEqual(votes.votes, 1)
        self.jira.remove_vote('QA-44')
        votes = self.jira.votes('QA-44')
        self.assertEqual(votes.votes, 0)

    @unittest.skip('test data doesn\'t support watching')
    def test_watchers(self):
        watchers = self.jira.watchers('BULK-1')
        self.assertEqual(watchers.watchCount, 18)

    @unittest.skip('test data doesn\'t support watching')
    def test_add_watcher(self):
        self.assertEqual(self.jira.watchers('QA-44').watchCount, 0)
        self.jira.add_watcher('QA-44', 'fred')
        self.assertEqual(self.jira.watchers('QA-44').watchCount, 1)

    @unittest.skip('test data doesn\'t support watching')
    def test_remove_watcher(self):
        self.assertEqual(self.jira.watchers('QA-44').watchCount, 1)
        self.jira.remove_watcher('QA-44', 'fred')
        self.assertEqual(self.jira.watchers('QA-44').watchCount, 0)

    def test_worklogs(self):
        worklogs = self.jira.worklogs('BULK-1')
        self.assertEqual(len(worklogs), 6)

    def test_worklog(self):
        worklog = self.jira.worklog('BULK-1', '10045')
        self.assertEqual(worklog.author.name, 'admin')
        self.assertEqual(worklog.timeSpent, '4d')

    def test_add_worklog(self):
        self.assertEqual(len(self.jira.worklogs('BULK-2')), 0)
        self.jira.add_worklog('BULK-2', '2h')
        self.assertEqual(len(self.jira.worklogs('BULK-2')), 1)

    def test_add_attachment(self):
        attach_count = len(self.jira.issue('BULK-3').fields.attachment)
        attachments = self.jira.add_attachment('BULK-3', open('__init__.py'))
        self.assertEqual(len(self.jira.issue('BULK-3').fields.attachment), attach_count + 1)


class IssueLinkTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_issue_link(self):
        link = self.jira.issue_link('10220')
        self.assertEqual(link.id, '10220')
        self.assertEqual(link.inwardIssue.id, '10924')

    def test_create_issue_link(self):
        self.jira.create_issue_link('Duplicate', 'BULK-1', 'BULK-2',
                comment={'body': 'Link comment!', 'visibility': {'type': 'role', 'value': 'Administrators'}})


class IssueLinkTypeTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_issue_link_types(self):
        link_types = self.jira.issue_link_types()
        self.assertEqual(len(link_types), 4)
        duplicate = find_by_id(link_types, '10001')
        self.assertEqual(duplicate.name, 'Duplicate')

    def test_issue_link_type(self):
        link_type = self.jira.issue_link_type('10002')
        self.assertEqual(link_type.id, '10002')
        self.assertEqual(link_type.name, 'Very long one')


class IssueTypesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_issue_types(self):
        types = self.jira.issue_types()
        self.assertEqual(len(types), 12)
        unq_issues = find_by_id(types, '6')
        self.assertEqual(unq_issues.name, 'UNQ-ISSUES')

    def test_issue_type(self):
        type = self.jira.issue_type('4')
        self.assertEqual(type.id, '4')
        self.assertEqual(type.name, 'Improvement')


class MyPermissionsTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('fred', 'fred'))

    def test_my_permissions(self):
        perms = self.jira.my_permissions()
        self.assertEqual(len(perms['permissions']), 38)

    def test_my_permissions_by_project(self):
        perms = self.jira.my_permissions(projectKey='BULK')
        self.assertEqual(len(perms['permissions']), 38)
        perms = self.jira.my_permissions(projectId='10031')
        self.assertEqual(len(perms['permissions']), 38)

    def test_my_permissions_by_issue(self):
        perms = self.jira.my_permissions(issueKey='BLUK-7')
        self.assertEqual(len(perms['permissions']), 38)
        perms = self.jira.my_permissions(issueId='11021')
        self.assertEqual(len(perms['permissions']), 38)


class PrioritiesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_priorities(self):
        priorities = self.jira.priorities()
        self.assertEqual(len(priorities), 5)

    def test_priority(self):
        priority = self.jira.priority('2')
        self.assertEqual(priority.id, '2')
        self.assertEqual(priority.name, 'Critical')


class ProjectTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_projects(self):
        projects = self.jira.projects()
        self.assertEqual(len(projects), 12)

    def test_project(self):
        project = self.jira.project('BOOK')
        self.assertEqual(project.id, '10540')
        self.assertEqual(project.name, 'Book Request')

    def test_project_avatars(self):
        avatars = self.jira.project_avatars('BULK')
        self.assertEqual(len(avatars['custom']), 1)
        self.assertEqual(len(avatars['system']), 12)

    def test_create_project_avatar(self):
        # Tests the end-to-end project avatar creation process: upload as temporary, confirm after cropping,
        # and selection.
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_project_avatar('XSS', filename, size, icon.read())
        self.assertIn('cropperOffsetX', props)
        self.assertIn('cropperOffsetY', props)
        self.assertIn('cropperWidth', props)
        self.assertTrue(props['needsCropping'])

        props['needsCropping'] = False
        avatar_props = self.jira.confirm_project_avatar('XSS', props)
        self.assertIn('id', avatar_props)

        self.jira.set_project_avatar('XSS', avatar_props['id'])

    def test_set_project_avatar(self):
        def find_selected_avatar(avatars):
            for avatar in avatars['system']:
                if avatar['isSelected']:
                    return avatar
            else:
                raise

        self.jira.set_project_avatar('XSS', '10000')
        avatars = self.jira.project_avatars('XSS')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10000')

        self.jira.set_project_avatar('XSS', '10001')
        avatars = self.jira.project_avatars('XSS')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10001')

    def test_project_components(self):
        components = self.jira.project_components('BULK')
        self.assertEqual(len(components), 2)
        bacon = find_by_id(components, '10003')
        self.assertEqual(bacon.id, '10003')
        self.assertEqual(bacon.name, 'Bacon')

    def test_project_versions(self):
        versions = self.jira.project_versions('BULK')
        self.assertEqual(len(versions), 6)
        love = find_by_id(versions, '10012')
        self.assertEqual(love.id, '10012')
        self.assertEqual(love.name, 'I love versions')

    def test_project_roles(self):
        roles = self.jira.project_roles('XSS')
        self.assertEqual(len(roles), 4)
        self.assertIn('Users', roles)

    def test_project_role(self):
        role = self.jira.project_role('XSS', '10010')
        self.assertEqual(role.id, 10010)
        self.assertEqual(role.name, 'Doco Team')


class ResolutionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_resolutions(self):
        resolutions = self.jira.resolutions()
        self.assertEqual(len(resolutions), 5)

    def test_resolution(self):
        resolution = self.jira.resolution('2')
        self.assertEqual(resolution.id, '2')
        self.assertEqual(resolution.name, 'Won\'t Fix')


class SearchTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_search_issues(self):
        issues = self.jira.search_issues('project=BULK')
        self.assertEqual(len(issues), 50) # default maxResults
        for issue in issues:
            self.assertTrue(issue.key.startswith('BULK'))

    def test_search_issues_maxResults(self):
        issues = self.jira.search_issues('project=XSS', maxResults=10)
        self.assertEqual(len(issues), 10)

    def test_search_issues_startAt(self):
        issues = self.jira.search_issues('project=BULK', startAt=90, maxResults=500)
        self.assertEqual(len(issues), 12)  # all but 12 issues in BULK

    def test_search_issues_field_limiting(self):
        issues = self.jira.search_issues('key=BULK-1', fields='summary,comment')
        self.assertTrue(hasattr(issues[0].fields, 'summary'))
        self.assertTrue(hasattr(issues[0].fields, 'comment'))
        self.assertFalse(hasattr(issues[0].fields, 'reporter'))
        self.assertFalse(hasattr(issues[0].fields, 'progress'))

    @unittest.skip('Skipping until I know how to handle the expandos')
    def test_search_issues_expandos(self):
        issues = self.jira.search_issues('key=BULK-1', expand=('names'))
        self.assertTrue(hasattr(issues[0], 'names'))
        self.assertFalse(hasattr(issues[0], 'schema'))


class SecurityLevelTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_security_level(self):
        sec_level = self.jira.security_level('10001')
        self.assertEqual(sec_level.id, '10001')
        self.assertEqual(sec_level.name, 'eee')


class ServerInfoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_server_info(self):
        server_info = self.jira.server_info()
        self.assertIn('baseUrl', server_info)
        self.assertIn('version', server_info)


class StatusTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_statuses(self):
        stati = self.jira.statuses()
        self.assertEqual(len(stati), 20)

    def test_status(self):
        status = self.jira.status('10004')
        self.assertEqual(status.id, '10004')
        self.assertEqual(status.name, '5555')


class UserTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_user(self):
        user = self.jira.user('fred')
        self.assertEqual(user.name, 'fred')
        self.assertEqual(user.emailAddress, 'fred@example.com')

    def test_search_assignable_users_for_projects(self):
        users = self.jira.search_assignable_users_for_projects('fred', 'BULK,XSS')
        self.assertEqual(len(users), 3)
        usernames = map(lambda user: user.name, users)
        self.assertIn('fred', usernames)
        self.assertIn('fred2', usernames)
        self.assertIn('fred&george', usernames)

    def test_search_assignable_users_for_projects_maxResults(self):
        users = self.jira.search_assignable_users_for_projects('fred', 'BULK,XSS', maxResults=1)
        self.assertEqual(len(users), 1)

    def test_search_assignable_users_for_projects_startAt(self):
        users = self.jira.search_assignable_users_for_projects('fred', 'BULK,XSS', startAt=1)
        self.assertEqual(len(users), 2)

    def test_search_assignable_users_for_issues_by_project(self):
        users = self.jira.search_assignable_users_for_issues('b', project='DMN')
        self.assertEqual(len(users), 2)
        usernames = map(lambda user: user.name, users)
        self.assertIn('admin', usernames)
        self.assertIn('aaa', usernames)

    def test_search_assignable_users_for_issues_by_project_maxResults(self):
        users = self.jira.search_assignable_users_for_issues('b', project='DMN', maxResults=1)
        self.assertEqual(len(users), 1)

    def test_search_assignable_users_for_issues_by_project_startAt(self):
        users = self.jira.search_assignable_users_for_issues('b', project='DMN', startAt=1)
        self.assertEqual(len(users), 1)

    def test_search_assignable_users_for_issues_by_issue(self):
        users = self.jira.search_assignable_users_for_issues('b', issueKey='BULK-1')
        self.assertEqual(len(users), 4)
        usernames = map(lambda user: user.name, users)
        self.assertIn('admin', usernames)
        self.assertIn('aaa', usernames)
        self.assertIn('hamish', usernames)
        self.assertIn('veenu', usernames)

    def test_search_assignable_users_for_issues_by_issue_maxResults(self):
        users = self.jira.search_assignable_users_for_issues('b', issueKey='BULK-1', maxResults=2)
        self.assertEqual(len(users), 2)

    def test_search_assignable_users_for_issues_by_issue_startAt(self):
        users = self.jira.search_assignable_users_for_issues('b', issueKey='BULK-1', startAt=2)
        self.assertEqual(len(users), 2)

    def test_user_avatars(self):
        avatars = self.jira.user_avatars('fred')
        self.assertEqual(len(avatars['system']), 24)
        self.assertEqual(len(avatars['custom']), 0)

    def test_create_user_avatar(self):
        # Tests the end-to-end user avatar creation process: upload as temporary, confirm after cropping,
        # and selection.
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar('admin', filename, size, icon.read())
        self.assertIn('cropperOffsetX', props)
        self.assertIn('cropperOffsetY', props)
        self.assertIn('cropperWidth', props)
        self.assertTrue(props['needsCropping'])

        props['needsCropping'] = False
        avatar_props = self.jira.confirm_user_avatar('admin', props)
        self.assertIn('id', avatar_props)
        self.assertEqual(avatar_props['owner'], 'admin')

        self.jira.set_user_avatar('admin', avatar_props['id'])

    def test_set_user_avatar(self):
        def find_selected_avatar(avatars):
            for avatar in avatars['system']:
                if avatar['isSelected']:
                    return avatar
            else:
                raise

        self.jira.set_user_avatar('fred', '10070')
        avatars = self.jira.user_avatars('fred')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10070')

        self.jira.set_user_avatar('fred', '10071')
        avatars = self.jira.user_avatars('fred')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10071')

    def test_search_users(self):
        users = self.jira.search_users('f')
        self.assertEqual(len(users), 3)
        usernames = map(lambda user: user.name, users)
        self.assertIn('fred&george', usernames)
        self.assertIn('fred', usernames)
        self.assertIn('fred2', usernames)

    def test_search_users_maxResults(self):
        users = self.jira.search_users('f', maxResults=2)
        self.assertEqual(len(users), 2)

    def test_search_users_startAt(self):
        users = self.jira.search_users('f', startAt=2)
        self.assertEqual(len(users), 1)

    def test_search_allowed_users_for_issue_by_project(self):
        users = self.jira.search_allowed_users_for_issue('w', projectKey='EVL')
        self.assertEqual(len(users), 5)

    def test_search_allowed_users_for_issue_by_issue(self):
        users = self.jira.search_allowed_users_for_issue('b', issueKey='BULK-1')
        self.assertEqual(len(users), 4)

    def test_search_allowed_users_for_issue_maxResults(self):
        users = self.jira.search_allowed_users_for_issue('w', projectKey='EVL', maxResults=2)
        self.assertEqual(len(users), 2)

    def test_search_allowed_users_for_issue_startAt(self):
        users = self.jira.search_allowed_users_for_issue('w', projectKey='EVL', startAt=4)
        self.assertEqual(len(users), 1)


class VersionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_create_version(self):
        version = self.jira.create_version('new version 1', 'BULK', releaseDate='2013-03-11',
                description='test version!')
        self.assertEqual(version.name, 'new version 1')
        self.assertEqual(version.description, 'test version!')
        self.assertEqual(version.releaseDate, '2013-03-11')

    def test_move_version(self):
        self.jira.move_version('10004', after=self.jira._get_url('version/10011'))
        self.jira.move_version('10004', position='Later')

        # trying to move a version in a different project should fail
        self.assertRaises(JIRAError, self.jira.move_version, '10003', self.jira._get_url('version/10011'))

    def test_version(self):
        version = self.jira.version('10003')
        self.assertEqual(version.id, '10003')
        self.assertEqual(version.name, '2.0')

    @unittest.skip('Versions don\'t seem to need expandos')
    def test_version_expandos(self):
        pass

    def test_version_count_related_issues(self):
        counts = self.jira.version_count_related_issues('10003')
        self.assertEqual(counts['issuesFixedCount'], 1)
        self.assertEqual(counts['issuesAffectedCount'], 1)

    def test_version_count_unresolved_issues(self):
        self.assertEqual(self.jira.version_count_unresolved_issues('10004'), 4)


class SessionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_session(self):
        user = self.jira.session()
        self.assertEqual(user.name, 'admin')

    def test_session_with_no_logged_in_user_raises(self):
        anon_jira = JIRA()
        self.assertRaises(JIRAError, anon_jira.session)

    @unittest.expectedFailure
    def test_kill_session(self):
        self.jira.kill_session()
        self.jira.session()


class WebsudoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JIRA(basic_auth=('admin', 'admin'))

    def test_kill_websudo(self):
        self.jira.kill_websudo()

    def test_kill_websudo_without_login_raises(self):
        anon_jira = JIRA()
        self.assertRaises(JIRAError, anon_jira.kill_websudo)


def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item['key'] == key:
            return seq_item

def find_by_id(seq, id):
    for seq_item in seq:
        if seq_item.id == id:
            return seq_item