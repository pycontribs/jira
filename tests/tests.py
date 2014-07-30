#!/usr/bin/env python
from __future__ import print_function
import os
import re
import sys
import time
import pip
import inspect
import logging
import getpass
from time import sleep


from six import print_ as print
from requests.exceptions import ConnectionError

#import sys
#from imp import reload
#reload(sys)  # Reload does the trick!
#sys.setdefaultencoding('UTF8')

if sys.version_info < (2, 7, 0):
    try:
        import unittest2 as unittest
    except ImportError:
        pip.main(['install', '--upgrade', '--user', 'unittest2'])
        import unittest2 as unittest
else:
    import unittest

try:
    import xmlrunner
    import requests
except ImportError:
    pip.main(['install', '--user', '--upgrade', 'tlslite', 'requests-oauthlib', 'requests', 'unittest-xml-reporting', 'xmlrunner'])
    import xmlrunner
    import requests

cmd_folder = os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], ".."))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

from jira.client import JIRA
from jira.exceptions import JIRAError
from jira.resources import Resource, cls_for_resource, Issue, Project, Role

TEST_ROOT = os.path.dirname(__file__)
TEST_ICON_PATH = os.path.join(TEST_ROOT, 'icon.png')
TEST_ATTACH_PATH = os.path.join(TEST_ROOT, '__init__.py')

OAUTH = False
CONSUMER_KEY = 'oauth-consumer'
KEY_CERT_FILE = '/home/bspeakmon/src/atlassian-oauth-examples/rsa.pem'
KEY_CERT_DATA = None
try:
    with open(KEY_CERT_FILE, 'r') as cert:
        KEY_CERT_DATA = cert.read()
    OAUTH = True
except:
    pass

def get_status_code(host, path="/", auth=None):
    """ This function retreives the status code of a website by requesting
        HEAD data from the host. This means that it only requests the headers.
        If the host cannot be reached or something else goes wrong, it returns
        None instead.
    """
    try:
        if not auth:
            r = requests.get(host + path)
        else:
            r = requests.get(host + path, auth=auth)
        return r.status_code
    except Exception:
        return None


"""
if CI_JIRA_ADMIN_USER:
    j = JIRA(options={'server': CI_JIRA_URL}, basic_auth=(CI_JIRA_ADMIN_USER, CI_JIRA_ADMIN_PASSWORD))
else:
    j = JIRA(options={'server': CI_JIRA_URL})

j.add_user('eviladmin', 'noreply@example.com', password='eviladmin')  # , fullname=None, sendEmail=False, active=True)
j.add_user_to_group('eviladmin', 'jira-administrators')
j.add_user('fred', 'noreply@example.com', password='fred')
j.delete_project("XSS")
j.delete_project("BULK")
j.create_project("XSS", "XSS")
r = j.create_project("BULK", "BULK")
print(r)
j.create_issue(project={'key': 'BULK'}, summary='issue 1 from BULK', issuetype={'name': 'Bug'})
j.create_issue(project={'key': 'BULK'}, summary='issue 2 from BULK', issuetype={'name': 'Bug'})
j.create_issue(project={'key': 'BULK'}, summary='issue 3 from BULK', issuetype={'name': 'Bug'})

"""

class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

class JiraTestManager(object):
    """
    Used to instantiate and populate the JIRA instance with data used by the unit tests.
    """
    # __metaclass__ = Singleton


    # __instance = None
    #
    # Singleton implementation
    # def __new__(cls, *args, **kwargs):
    #     if not cls.__instance:
    #         cls.__instance = super(JiraTestManager, cls).__new__(
    #                             cls, *args, **kwargs)
    #     return cls.__instance

    #  Implementing some kind of Singleton, to prevent test initialization
    #  http://stackoverflow.com/questions/31875/is-there-a-simple-elegant-way-to-define-singletons-in-python/33201#33201
    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state

        if not self.__dict__:
            self.initialized = 0

            try:
                try:
                    import settings
                except:
                    pass

                if 'CI_JIRA_URL' in os.environ:
                    self.CI_JIRA_URL = os.environ['CI_JIRA_URL']
                else:
                    self.CI_JIRA_URL = "http://localhost:2990"

                if 'CI_JIRA_ADMIN' in os.environ:
                    self.CI_JIRA_ADMIN = os.environ['CI_JIRA_ADMIN']
                else:
                    self.CI_JIRA_ADMIN = None

                if 'CI_JIRA_ADMIN_PASSWORD' in os.environ:
                    self.CI_JIRA_ADMIN_PASSWORD = os.environ['CI_JIRA_ADMIN_PASSWORD']
                else:
                    self.CI_JIRA_ADMIN_PASSWORD = None


                if 'CI_JIRA_USER' in os.environ:
                    self.CI_JIRA_USER = os.environ['CI_JIRA_USER']
                else:
                    self.CI_JIRA_USER = None

                if 'CI_JIRA_USER_PASSWORD' in os.environ:
                    self.CI_JIRA_USER_PASSWORD = os.environ['CI_JIRA_USER_PASSWORD']
                else:
                    self.CI_JIRA_USER_PASSWORD = None



                if OAUTH:
                    self.jira_admin = JIRA(oauth={
                        'access_token': 'hTxcwsbUQiFuFALf7KZHDaeAJIo3tLUK',
                        'access_token_secret': 'aNCLQFP3ORNU6WY7HQISbqbhf0UudDAf',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA,
                    })
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_admin = JIRA(self.CI_JIRA_URL, basic_auth=(self.CI_JIRA_ADMIN, self.CI_JIRA_ADMIN_PASSWORD), logging=False, validate=True)
                    else:
                        self.jira_admin = JIRA(self.CI_JIRA_URL, validate=True, logging=False)
                if self.jira_admin.current_user() != self.CI_JIRA_ADMIN:
                    #self.jira_admin.
                    self.initialized = 1
                    sys.exit(3)

                if OAUTH:
                    self.jira_sysadmin = JIRA(oauth={
                        'access_token': '4ul1ETSFo7ybbIxAxzyRal39cTrwEGFv',
                        'access_token_secret': 'K83jBZnjnuVRcfjBflrKyThJa0KSjSs2',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA,
                    }, logging=False)
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_sysadmin = JIRA(self.CI_JIRA_URL, basic_auth=(self.CI_JIRA_ADMIN, self.CI_JIRA_ADMIN_PASSWORD), logging=False, validate=True)
                    else:
                        self.jira_sysadmin = JIRA(self.CI_JIRA_URL, logging=False)

                if OAUTH:
                    self.jira_normal = JIRA(oauth={
                        'access_token': 'ZVDgYDyIQqJY8IFlQ446jZaURIz5ECiB',
                        'access_token_secret': '5WbLBybPDg1lqqyFjyXSCsCtAWTwz1eD',
                        'consumer_key': CONSUMER_KEY,
                        'key_cert': KEY_CERT_DATA,
                    })
                else:
                    if self.CI_JIRA_ADMIN:
                        self.jira_normal = JIRA(self.CI_JIRA_URL, basic_auth=(self.CI_JIRA_USER, self.CI_JIRA_USER_PASSWORD), validate=True, logging=False)
                    else:
                        self.jira_normal = JIRA(self.CI_JIRA_URL, validate=True, logging=False)

                # now we need some data to start with for the tests

                # jira project key is max 10 chars, no letter.
                # [0] always "Z"
                # [1-6] username running the tests (hope we will not collide)
                # [7-8] python version A=0, B=1,..
                # [9] A,B -- we may need more than one project

                prefix = 'Z' + (re.sub ("[^A-Z]", "", getpass.getuser().upper()))[0:6] + \
                    chr(ord('A') + sys.version_info[0]) + \
                    chr(ord('A') + sys.version_info[1])

                self.project_a = prefix + 'A' # old XSS
                self.project_a_name = "Test user=%s python=%s.%s A" % (getpass.getuser(), sys.version_info[0], sys.version_info[1])
                self.project_b_name = "Test user=%s python=%s.%s B" % (getpass.getuser(), sys.version_info[0], sys.version_info[1])
                self.project_b = prefix + 'B' # old BULK


                # TODO: fin a way to prevent SecurityTokenMissing for On Demand https://jira.atlassian.com/browse/JRA-39153
                # self.jira_admin.delete_project(self.project_a)
                # self.jira_admin.delete_project(self.project_b)

                try:
                    #assert self.jira_admin.create_project(self.project_a, self.project_a_name) is True, "Failed to create %s" % self.project_a
                    self.jira_admin.create_project(self.project_a, self.project_a_name)
                except:
                    pass
                try:
                    #assert self.jira_admin.create_project(self.project_b, self.project_b_name) is  True, "Failed to create %s" % self.project_b
                    self.jira_admin.create_project(self.project_b, self.project_b_name)
                except:
                    pass

                logging.info("ccc")
                self.project_b_issue1 = self.jira_admin.create_issue(project={'key': self.project_b}, summary='issue 1 from %s' % self.project_b, issuetype={'name': 'Bug'}).key
                logging.info("ccc2")
                self.project_b_issue2 = self.jira_admin.create_issue(project={'key': self.project_b}, summary='issue 2 from %s' % self.project_b, issuetype={'name': 'Bug'}).key
                logging.info("ccc3")
                self.project_b_issue3 = self.jira_admin.create_issue(project={'key': self.project_b}, summary='issue 3 from %s' % self.project_b, issuetype={'name': 'Bug'}).key
                logging.info("ccc4")

            except Exception as e:
                logging.fatal("Basic test setup failed, that's FATAL!. %s" % e)
                self.initialized = 1
                sys.exit(3)

            self.initialized = 1

        else:
            # already exist but we need to be sure it was initialized
            counter = 0
            while not self.initialized:
                sleep(1)
                counter += 1
                if counter > 60:
                    logging.fatal("Something is clearly not right with initialization, killing the tests to prevent a deadlock.")
                    sys.exit(3)


def find_by_key(seq, key):
    for seq_item in seq:
        if seq_item['key'] == key:
            return seq_item

def find_by_key_value(seq, key):
    for seq_item in seq:
        if seq_item.key == key:
            return seq_item


def find_by_id(seq, id):
    for seq_item in seq:
        if seq_item.id == id:
            return seq_item

def find_by_name(seq, name):
    for seq_item in seq:
        if seq_item['name'] == name:
            return seq_item

"""
class UniversalResourceTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.test_manager = JiraTestManager()

    def test_universal_find_existing_resource(self):
        resource = self.jira.find('issue/{0}', self.test_manager.project_b_issue1)
        issue = self.jira.issue(self.test_manager.project_b_issue1)
        self.assertEqual(resource.self, issue.self)
        self.assertEqual(resource.key, issue.key)

    def test_universal_find_custom_resource(self):
        resource = Resource('nope/{0}', self.jira._options, None)  # don't need an actual session
        self.assertEqual('https://pycontribs.atlassian.net/rest/api/2/nope/666', str (resource._url(('666',))))

    def test_find_invalid_resource_raises_exception(self):
        with self.assertRaises(JIRAError) as cm:
            self.jira.find('woopsydoodle/{0}', '666')

        ex = cm.exception
        self.assertEqual(ex.status_code, 404)
        self.assertIsNotNone(ex.text)
        self.assertEqual(ex.url, 'https://pycontribs.atlassian.net/rest/api/2/woopsydoodle/666')

    def test_verify_works_with_https(self):
        self.jira = JIRA(options={'server': 'https://jira.atlassian.com'})

    def test_verify_fails_without_https(self):
        self.assertRaises (JIRAError, JIRA, options={'server': 'https://www.yahoo.com'})

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
        self.jira = JiraTestManager().jira_admin

    def test_application_properties(self):
        props = self.jira.application_properties()
        self.assertEqual(len(props), 30)

    def test_application_property(self):
        clone_prefix = self.jira.application_properties(key='jira.lf.text.headingcolour')
        self.assertEqual(clone_prefix['value'], '#292929')

    def test_set_application_property(self):
        prop = 'jira.lf.favicon.hires.url'
        self.jira.set_application_property(prop, '/Tjira-favicon-hires.png')
        self.assertEqual(self.jira.application_properties(key=prop)['value'], '/Tjira-favicon-hires.png')
        self.jira.set_application_property(prop, '/jira-favicon-hires.png')
        self.assertEqual(self.jira.application_properties(key=prop)['value'], '/jira-favicon-hires.png')

    def test_setting_bad_property_raises(self):
        prop = 'random.nonexistent.property'
        self.assertRaises(JIRAError, self.jira.set_application_property, prop, '666')

class AttachmentTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1

    def test_attachment(self):
        issue = self.jira.issue(self.issue_1)
        attachment = self.jira.add_attachment(issue, open(TEST_ATTACH_PATH), "new test attachment")
        new_attachment = self.jira.attachment(attachment.id)
        self.assertEqual(new_attachment.filename, 'new test attachment')
        self.assertEqual(new_attachment.size, 25)
        attachment.delete()

    def test_attachment_meta(self):
        meta = self.jira.attachment_meta()
        self.assertTrue(meta['enabled'])
        self.assertEqual(meta['uploadLimit'], 10485760)

    def test_add_attachment(self):
        issue = self.jira.issue(self.issue_1)
        attach_count = len(issue.fields.attachment)
        attachment = self.jira.add_attachment(issue, open(TEST_ATTACH_PATH))
        self.assertIsNotNone(attachment)
        self.assertEqual(len(self.jira.issue(self.issue_1).fields.attachment), attach_count + 1)

    def test_delete(self):
        attach_count = len(self.jira.issue(self.issue_1).fields.attachment)
        attachment = self.jira.add_attachment(self.issue_1, open(TEST_ATTACH_PATH))
        self.assertEqual(len(self.jira.issue(self.issue_1).fields.attachment), attach_count + 1)
        attachment.delete()
        self.assertEqual(len(self.jira.issue(self.issue_1).fields.attachment), attach_count)

class ComponentTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 =  self.test_manager.project_b_issue2

    def test_component(self):
        component = self.jira.component('10001')
        self.assertEqual(component.name, 'Test Suites')

    def test_create_component(self):
        proj = self.jira.project(self.project_b)
        component = self.jira.create_component('Project b test component', proj, description='test!!',
                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
        self.assertEqual(component.name, 'Project b test component')
        self.assertEqual(component.description, 'test!!')
        self.assertEqual(component.assigneeType, 'COMPONENT_LEAD')
        self.assertFalse(component.isAssigneeTypeValid)
        component.delete()

#COmponents field can't be modified from issue.update
#    def test_component_count_related_issues(self):
#        component = self.jira.create_component('PROJECT_B_TEST', self.project_b, description='test!!',
#                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
#        issue1 = self.jira.issue(self.issue_1)
#        issue2 = self.jira.issue(self.issue_2)
#        (issue1.update ({'components': ['PROJECT_B_TEST']}))
#        (issue2.update (components = ['PROJECT_B_TEST']))
#        issue_count = self.jira.component_count_related_issues(component.id)
#        self.assertEqual(issue_count, 2)
#        component.delete()

    def test_update(self):
        component = self.jira.create_component('To be updated', self.project_b, description='stand by!', leadUserName='ci-admin')
        component.update(name='Updated!', description='It is done.', leadUserName='ci-dmin')
        self.assertEqual(component.name, 'Updated!')
        self.assertEqual(component.description, 'It is done.')
        self.assertEqual(component.lead.name, 'ci-admin')
        component.delete()

    def test_delete(self):
        component = self.jira.create_component('To be deleted', self.project_b, description='not long for this world')
        id = component.id
        component.delete()
        self.assertRaises(JIRAError, self.jira.component, id)

class CustomFieldOptionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_custom_field_option(self):
        option = self.jira.custom_field_option('10001')
        self.assertEqual(option.value, 'To Do')

class DashboardTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_dashboards(self):
        dashboards = self.jira.dashboards()
        self.assertEqual(len(dashboards), 2)

    def test_dashboards_filter(self):
        dashboards = self.jira.dashboards(filter='my')
        self.assertEqual(len(dashboards), 2)
        self.assertEqual(dashboards[0].id, '10101')

    def test_dashboards_startAt(self):
        dashboards = self.jira.dashboards(startAt=1, maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboards_maxResults(self):
        dashboards = self.jira.dashboards(maxResults=1)
        self.assertEqual(len(dashboards), 1)

    def test_dashboard(self):
        dashboard = self.jira.dashboard('10101')
        self.assertEqual(dashboard.id, '10101')
        self.assertEqual(dashboard.name, 'Another test dashboard')

class FieldsTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_fields(self):
        fields = self.jira.fields()
        self.assertEqual(len(fields), 64)


class FilterTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.project_b = self.test_manager.project_b
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 =  self.test_manager.project_b_issue2

    def test_filter(self):
        jql = "project = %s and component is not empty" %self.project_b
        filter = self.jira.create_filter(name = "Some test filter", description = "just some test filter",
                jql = jql, favourite = False)
        self.assertEqual(filter.name, 'Some test filter')
        self.assertEqual(filter.owner.name, 'ci-admin')
        filter.delete()

    def test_favourite_filters(self):
        filters = self.jira.favourite_filters()
        initial_len = len(filters)
        jql = "project = %s and component is not empty" %self.project_b
        filter = self.jira.create_filter(name = "Some test filter", description = "just some test filter",
                jql = jql, favourite = True)
        self.assertEqual(len(self.jira.favourite_filters()), initial_len + 1)
        filter.delete()
        self.assertEqual(len(self.jira.favourite_filters()), initial_len)

class GroupsTest(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_groups(self):
        groups = self.jira.groups()
        self.assertGreaterEqual(groups['total'], 0)

    def test_groups_for_users(self):
        groups = self.jira.groups('users')
        self.assertIsNotNone(find_by_name(groups['groups'], 'users'))

    def test_groups_with_exclude(self):
        groups = self.jira.groups('users')
        new_groups = self.jira.groups('users', exclude='users')
        self.assertEqual(groups['total'] - 1, new_groups['total'])

    def test_groups_for_jira(self):
        groups = self.jira.groups('jira')
        self.assertIsNotNone(find_by_name(groups['groups'], 'jira-users'))

class IssueTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_admin
        self.jira_normal = self.test_manager.jira_normal
        self.project_b = self.test_manager.project_b
        self.project_a = self.test_manager.project_a
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 =  self.test_manager.project_b_issue2
        self.issue_3 = self.test_manager.project_b_issue3

    def test_issue(self):
        issue = self.jira.issue(self.issue_1)
        self.assertEqual(issue.key, self.issue_1)
        self.assertEqual(issue.fields.summary, 'issue 1 from %s' %self.project_b)

    def test_issue_field_limiting(self):
        issue = self.jira.issue(self.issue_2, fields='summary,comment')
        self.assertEqual(issue.fields.summary, 'issue 2 from %s' %self.project_b)
        comment1 = self.jira.add_comment(issue, 'First comment') 
        comment2 = self.jira.add_comment(issue, 'Second comment') 
        comment3 = self.jira.add_comment(issue, 'Third comment') 
        new_issue = self.jira.issue(self.issue_2, fields = 'summary,comment')
        self.assertEqual(new_issue.fields.comment.total, 3)
        self.assertFalse(hasattr(issue.fields, 'reporter'))
        self.assertFalse(hasattr(issue.fields, 'progress'))
        comment1.delete()
        comment2.delete()
        comment3.delete()
    
    def test_issue_expandos(self):
        issue = self.jira.issue(self.issue_1, expand=('editmeta', 'schema'))
        self.assertTrue(hasattr(issue, 'editmeta'))
        self.assertTrue(hasattr(issue, 'schema'))
        self.assertFalse(hasattr(issue, 'changelog'))

    def test_create_issue_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue created',
                                       description='blahery', issuetype={'name': 'Bug'}, customfield_10022 = 'XSS')
        self.assertEqual(issue.fields.summary, 'Test issue created')
        self.assertEqual(issue.fields.description, 'blahery')
        self.assertEqual(issue.fields.issuetype.name, 'Bug')
        self.assertEqual(issue.fields.project.key, self.project_b)
        self.assertEqual(issue.fields.customfield_10022, 'XSS')
        issue.delete()

    def test_create_issue_with_fielddict(self):
        fields = {
            'project': {
                'key': self.project_b
            },
            'summary': 'Issue created from field dict',
            'description': "Some new issue for test",
            'issuetype': {
                'name': 'Bug'
            },
            'customfield_10022': 'XSS',
            'priority': {
                'name': 'Major'
            }
        }
        issue = self.jira.create_issue(fields=fields)
        self.assertEqual(issue.fields.summary, 'Issue created from field dict')
        self.assertEqual(issue.fields.description, "Some new issue for test")
        self.assertEqual(issue.fields.issuetype.name, 'Bug')
        self.assertEqual(issue.fields.project.key, self.project_b)
        self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.priority.name, 'Major')
        issue.delete()

    def test_create_issue_without_prefetch(self):
        issue = self.jira.create_issue(prefetch=False, project={'key': self.project_b}, summary='Test issue created',
                                       description='blahery', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        self.assertTrue(hasattr(issue, 'self'))
        self.assertFalse(hasattr(issue, 'fields'))
        self.assertFalse(hasattr(issue, 'customfield_10022'))
        self.assertTrue(hasattr(issue, 'raw'))
        issue.delete()

    def test_update_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue for updating',
                                       description='Will be updated shortly', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        issue.update(summary='Updated summary', description='Now updated', issuetype={'name': 'Improvement'})
        self.assertEqual(issue.fields.summary, 'Updated summary')
        self.assertEqual(issue.fields.description, 'Now updated')
        self.assertEqual(issue.fields.issuetype.name, 'Improvement')
        self.assertEqual(issue.fields.customfield_10022, 'XSS')
        self.assertEqual(issue.fields.project.key, self.project_b)
        issue.delete()

    def test_update_with_fielddict(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue for updating',
                description='Will be updated shortly', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        fields = {
            'summary': 'Issue is updated',
            'description': "it sure is",
            'issuetype': {
                'name': 'Improvement'
            },
            'customfield_10022': 'DOC',
            'priority': {
                'name': 'Major'
            }
        }
        issue.update(fields=fields)
        self.assertEqual(issue.fields.summary, 'Issue is updated')
        self.assertEqual(issue.fields.description, 'it sure is')
        self.assertEqual(issue.fields.issuetype.name, 'Improvement')
        self.assertEqual(issue.fields.customfield_10022, 'DOC')
        self.assertEqual(issue.fields.priority.name, 'Major')
        issue.delete()

    def test_delete(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue created',
                                       description='Not long for this world', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        key = issue.key
        issue.delete()
        self.assertRaises(JIRAError, self.jira.issue, key)

    def test_createmeta(self):
        meta = self.jira.createmeta()
        ztravisdeb_proj = find_by_key(meta['projects'], self.project_b)
        self.assertEqual(len(ztravisdeb_proj['issuetypes']), 8)

    def test_createmeta_filter_by_projectkey_and_name(self):
        meta = self.jira.createmeta(projectKeys=self.project_b, issuetypeNames='Bug')
        self.assertEqual(len(meta['projects']), 1)
        self.assertEqual(len(meta['projects'][0]['issuetypes']), 1)

    def test_createmeta_filter_by_projectkeys_and_name(self):
        meta = self.jira.createmeta(projectKeys=(self.project_a, self.project_b), issuetypeNames='Improvement')
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertEqual(len(project['issuetypes']), 1)

    def test_createmeta_filter_by_id(self):
        projects = self.jira.projects()
        proja = find_by_key_value(projects, self.project_a)
        projb = find_by_key_value(projects, self.project_b)
        meta = self.jira.createmeta(projectIds=(proja.id, projb.id), issuetypeIds=('3', '4', '5'))
        self.assertEqual(len(meta['projects']), 2)
        for project in meta['projects']:
            self.assertEqual(len(project['issuetypes']), 3)

    def test_createmeta_expando(self):
        # limit to SCR project so the call returns promptly
        meta = self.jira.createmeta(projectKeys=self.project_b, expand='projects.issuetypes.fields')
        self.assertTrue('fields' in meta['projects'][0]['issuetypes'][0])

    def test_assign_issue(self):
        self.assertIsNone(self.jira.assign_issue(self.issue_1, 'ci-admin'))
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee.name, 'ci-admin')

    def test_assign_issue_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        self.assertIsNone(self.jira.assign_issue(issue, 'ci-admin'))
        self.assertEqual(self.jira.issue(self.issue_1).fields.assignee.name, 'ci-admin')

    def test_assign_to_bad_issue_raises(self):
        self.assertRaises(JIRAError, self.jira.assign_issue, 'NOPE-1', 'notauser')
    
    def test_comments(self):
        issue = self.jira.issue(self.issue_1)
        comment1 = self.jira.add_comment(self.issue_1, 'First comment') 
        comment2 = self.jira.add_comment(self.issue_1, 'Second comment') 
        comment3 = self.jira.add_comment(self.issue_1, 'Third comment') 
        comment4 = self.jira.add_comment(self.issue_1, 'Fourth comment') 
        comments = self.jira.comments(self.issue_1)
        self.assertEqual(len(comments), 4)
        comment1.delete()
        comment2.delete()
        comment3.delete()
        comment4.delete()
        issue = self.jira.issue(self.issue_2)
        comment1 = self.jira.add_comment(self.issue_2, 'First comment') 
        comment2 = self.jira.add_comment(self.issue_2, 'Second comment') 
        comment3 = self.jira.add_comment(self.issue_2, 'Third comment') 
        comments = self.jira.comments(self.issue_2)
        self.assertEqual(len(comments), 3)
        comment1.delete()
        comment2.delete()
        comment3.delete()

    def test_comments_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        comment1 = self.jira.add_comment(issue, 'First comment') 
        comment2 = self.jira.add_comment(issue, 'Second comment') 
        comment3 = self.jira.add_comment(issue, 'Third comment') 
        comment4 = self.jira.add_comment(issue, 'Fourth comment') 
        new_issue = self.jira.issue(self.issue_1)
        comments = self.jira.comments(new_issue)
        self.assertEqual(len(comments), 4)
        comment1.delete()
        comment2.delete()
        comment3.delete()
        comment4.delete()
        issue = self.jira.issue(self.issue_2)
        comment1 = self.jira.add_comment(issue, 'First comment') 
        comment2 = self.jira.add_comment(issue, 'Second comment') 
        comment3 = self.jira.add_comment(issue, 'Third comment') 
        new_issue = self.jira.issue(self.issue_2)
        comments = self.jira.comments(new_issue)
        self.assertEqual(len(comments), 3)
        comment1.delete()
        comment2.delete()
        comment3.delete()

    def test_comment(self):
        comment = self.jira.add_comment(self.issue_1, 'just another test commnet')
        new_comment = self.jira.comment(self.issue_1, str(comment))
        self.assertTrue(new_comment.body.startswith('just another'))
        comment.delete()

    def test_comment_with_issue_obj(self):
        comment = self.jira.add_comment(self.issue_2, 'just another test commnet')
        issue = self.jira.issue(self.issue_2)
        new_comment = self.jira.comment(issue, str(comment))
        self.assertTrue(comment.body.startswith('just ano'))
        comment.delete()

    def test_add_comment(self):
        comment = self.jira.add_comment(self.issue_3, 'a test comment!',
                                        visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'a test comment!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_add_comment_with_issue_obj(self):
        issue = self.jira.issue(self.issue_3)
        comment = self.jira.add_comment(issue, 'a new test comment!',
                                        visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'a new test comment!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_update_comment(self):
        comment = self.jira.add_comment(self.issue_3, 'updating soon!')
        comment.update(body='updated!', visibility={'type': 'role', 'value': 'Administrators'})
        self.assertEqual(comment.body, 'updated!')
        self.assertEqual(comment.visibility.type, 'role')
        self.assertEqual(comment.visibility.value, 'Administrators')
        comment.delete()

    def test_delete_comment(self):
        c_len = len(self.jira.comments(self.issue_3))
        comment = self.jira.add_comment(self.issue_3, 'To be deleted!')
        comment.delete()
        self.assertEqual(len (self.jira.comments(self.issue_3)), c_len)

    def test_editmeta(self):
        meta = self.jira.editmeta(self.issue_1)
        self.assertEqual(len(meta['fields']), 18)
        self.assertTrue('customfield_10007' in meta['fields'])
        self.assertTrue('customfield_10022' in meta['fields'])

    def test_editmeta_with_issue_obj(self):
        issue = self.jira.issue(self.issue_2)
        meta = self.jira.editmeta(issue)
        self.assertEqual(len(meta['fields']), 18)
        self.assertTrue('customfield_10022' in meta['fields'])
        self.assertTrue('customfield_10007' in meta['fields'])

#Nothing from remote link works
#    def test_remote_links(self):
#        self.jira.add_remote_link ('ZTRAVISDEB-3', globalId='python-test:story.of.horse.riding',
#        links = self.jira.remote_links('QA-44')
#        self.assertEqual(len(links), 1)
#        links = self.jira.remote_links('BULK-1')
#        self.assertEqual(len(links), 0)
#
#    @unittest.skip("temporary disabled")
#    def test_remote_links_with_issue_obj(self):
#        issue = self.jira.issue('QA-44')
#        links = self.jira.remote_links(issue)
#        self.assertEqual(len(links), 1)
#        issue = self.jira.issue('BULK-1')
#        links = self.jira.remote_links(issue)
#        self.assertEqual(len(links), 0)
#
#    @unittest.skip("temporary disabled")
#    def test_remote_link(self):
#        link = self.jira.remote_link('QA-44', '10000')
#        self.assertEqual(link.id, 10000)
#        self.assertTrue(hasattr(link, 'globalId'))
#        self.assertTrue(hasattr(link, 'relationship'))
#
#    @unittest.skip("temporary disabled")
#    def test_remote_link_with_issue_obj(self):
#        issue = self.jira.issue('QA-44')
#        link = self.jira.remote_link(issue, '10000')
#        self.assertEqual(link.id, 10000)
#        self.assertTrue(hasattr(link, 'globalId'))
#        self.assertTrue(hasattr(link, 'relationship'))
#
#    @unittest.skip("temporary disabled")
#    def test_add_remote_link(self):
#        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
#        # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = self.jira.remote_link('BULK-3', link.id)
#        self.assertEqual(link.application.name, 'far too silly')
#        self.assertEqual(link.application.type, 'sketch')
#        self.assertEqual(link.object.url, 'http://google.com')
#        self.assertEqual(link.object.title, 'googlicious!')
#        self.assertEqual(link.relationship, 'mousebending')
#        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
#
#    @unittest.skip("temporary disabled")
#    def test_add_remote_link_with_issue_obj(self):
#        issue = self.jira.issue('BULK-3')
#        link = self.jira.add_remote_link(issue, globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
#        # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = self.jira.remote_link(issue, link.id)
#        self.assertEqual(link.application.name, 'far too silly')
#        self.assertEqual(link.application.type, 'sketch')
#        self.assertEqual(link.object.url, 'http://google.com')
#        self.assertEqual(link.object.title, 'googlicious!')
#        self.assertEqual(link.relationship, 'mousebending')
#        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
#
#    @unittest.skip("temporary disabled")
#    def test_update_remote_link(self):
#        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
#        # creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = self.jira.remote_link('BULK-3', link.id)
#        link.update(object={'url': 'http://yahoo.com', 'title': 'yahooery'}, globalId='python-test:updated.id',
#                    relationship='cheesing')
#        self.assertEqual(link.globalId, 'python-test:updated.id')
#        self.assertEqual(link.relationship, 'cheesing')
#        self.assertEqual(link.object.url, 'http://yahoo.com')
#        self.assertEqual(link.object.title, 'yahooery')
#        link.delete()
#
#    @unittest.skip("temporary disabled")
#    def test_delete_remove_link(self):
#        link = self.jira.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
#        _id = link.id
#        link.delete()
#        self.assertRaises(JIRAError, self.jira.remote_link, 'BULK-3', _id)

    def test_transitions(self):
        transitions = self.jira.transitions(self.issue_2)
        self.assertEqual(len(transitions), 3)

    def test_transitions_with_issue_obj(self):
        issue = self.jira.issue(self.issue_2)
        transitions = self.jira.transitions(issue)
        self.assertEqual(len(transitions), 3)

    def test_transition(self):
        transition = self.jira.transitions(self.issue_2, '5')
        self.assertEqual(transition[0]['name'], 'Resolve Issue')

    def test_transition_expand(self):
        transition = self.jira.transitions(self.issue_2, '5', expand=('transitions.fields'))
        self.assertTrue('fields' in transition[0])

    def test_transition_issue_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue for transition created',
                                       description='blahery', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        self.jira.transition_issue(issue.key, '2', assignee={'name': 'ci-admin'})
        issue = self.jira.issue(issue.key)
        self.assertEqual(issue.fields.assignee.name, 'ci-admin')
        self.assertEqual(issue.fields.status.id, '6')    # issue 'Closed'

    def test_transition_issue_obj_with_fieldargs(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue for transition created',
                                       description='blahery', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        self.jira.transition_issue(issue, '2', assignee={'name': 'ci-admin'})
        issue = self.jira.issue(issue.key)
        self.assertEqual(issue.fields.assignee.name, 'ci-admin')
        self.assertEqual(issue.fields.status.id, '6') 

    def test_transition_issue_with_fielddict(self):
        issue = self.jira.create_issue(project={'key': self.project_b}, summary='Test issue for transition created',
                                       description='blahery', issuetype={'name': 'Bug'}, customfield_10022='XSS')
        fields = {
            'assignee': {
                'name': 'ci-admin'
            }
        }
        self.jira.transition_issue(issue.key, '5', fields=fields)
        issue = self.jira.issue(issue.key)
        self.assertEqual(issue.fields.assignee.name, 'ci-admin')
        self.assertEqual(issue.fields.status.id, '5')

    def test_votes(self):
        votes = self.jira.votes(self.issue_1)
        self.assertEqual(votes.votes, 0)

    def test_votes_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        votes = self.jira.votes(issue)
        self.assertEqual(votes.votes, 0)

    def test_add_vote(self):
        votes = self.jira.votes(self.issue_2)
        init_len = votes.votes
        self.jira_normal.add_vote(self.issue_2)
        votes = self.jira.votes(self.issue_2)
        self.assertEqual(votes.votes, init_len + 1)
        self.jira_normal.remove_vote(self.issue_2)

    def test_add_vote_with_issue_obj(self):
        issue = self.jira.issue(self.issue_2)
        votes = self.jira.votes(issue)
        init_len = votes.votes
        self.jira_normal.add_vote(issue)
        votes = self.jira.votes(issue)
        self.assertEqual(votes.votes, init_len + 1)
        self.jira_normal.remove_vote(self.issue_2)

    def test_remove_vote(self):
        self.jira_normal.add_vote(self.issue_2)
        votes = self.jira.votes(self.issue_2)
        init_len = votes.votes
        self.jira_normal.remove_vote(self.issue_2)
        votes = self.jira.votes('ZTRAVISCGB-172')
        self.assertEqual(votes.votes, init_len - 1)

    def test_remove_vote_with_issue_obj(self):
        self.jira_normal.add_vote(self.issue_2)
        issue = self.jira.issue(self.issue_2)
        votes = self.jira.votes(issue)
        init_len = votes.votes
        self.jira_normal.remove_vote(issue)
        votes = self.jira.votes(issue)
        self.assertEqual(votes.votes, init_len - 1)

    def test_watchers(self):
        watchers = self.jira.watchers(self.issue_1)
        self.assertEqual(watchers.watchCount, 1)

    def test_watchers_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        watchers = self.jira.watchers(issue)
        self.assertEqual(watchers.watchCount, 1)

    def test_add_watcher(self):
        init_watchers = self.jira.watchers(self.issue_1).watchCount
        self.jira.add_watcher(self.issue_1, 'ci-user')
        self.assertEqual(self.jira.watchers(self.issue_1).watchCount, init_watchers + 1)
        self.jira.remove_watcher(self.issue_1, 'ci-user')

    def test_remove_watcher(self):
        self.jira.add_watcher(self.issue_1, 'ci-user')
        init_watchers = self.jira.watchers(self.issue_1).watchCount
        self.jira.remove_watcher(self.issue_1, 'ci-user')
        self.assertEqual(self.jira.watchers(self.issue_1).watchCount, init_watchers - 1)

    def test_add_watcher_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        init_watchers = self.jira.watchers(issue).watchCount
        self.jira.add_watcher(issue, 'ci-user')
        self.assertEqual(self.jira.watchers(issue).watchCount, init_watchers + 1)
        self.jira.remove_watcher(issue, 'ci-user')

    def test_remove_watcher_with_issue_obj(self):
        issue = self.jira.issue(self.issue_1)
        self.jira.add_watcher(issue, 'ci-user')
        init_watchers = self.jira.watchers(issue).watchCount
        self.jira.remove_watcher(issue, 'ci-admin')
        self.assertEqual(self.jira.watchers(issue).watchCount, init_watchers - 1)

#add worklog is not working for python2.6
#    def test_worklogs(self):
#        worklog = self.jira.add_worklog(self.issue_1, '2h')
#        worklogs = self.jira.worklogs(self.issue_1)
#        self.assertEqual(len(worklogs), 1)
#        worklog.delete()
#
#    def test_worklogs_with_issue_obj(self):
#        issue = self.jira.issue(self.issue_1)
#        worklog = self.jira.add_worklog(issue, '2h')
#        worklogs = self.jira.worklogs(issue)
#        self.assertEqual(len(worklogs), 1)
#        worklog.delete()
#
#    def test_worklog(self):
#        worklog = self.jira.add_worklog(self.issue_1, '1d 2h')
#        new_worklog = self.jira.worklog(self.issue_1, str(worklog))
#        self.assertEqual(new_worklog.author.name, 'ci-admin')
#        self.assertEqual(new_worklog.timeSpent, '1d 2h')
#        worklog.delete()
#
#    def test_worklog_with_issue_obj(self):
#        issue = self.jira.issue(self.issue_1)
#        worklog = self.jira.add_worklog(issue, '1d 2h')
#        new_worklog = self.jira.worklog(issue, str(worklog))
#        self.assertEqual(new_worklog.author.name, 'ci-admin')
#        self.assertEqual(new_worklog.timeSpent, '1d 2h')
#        worklog.delete()
#
#    def test_add_worklog(self):
#        worklog_count = len(self.jira.worklogs(self.issue_2))
#        worklog = self.jira.add_worklog(self.issue_2, '2h')
#        self.assertIsNotNone(worklog)
#        self.assertEqual(len(self.jira.worklogs(self.issue_2)), worklog_count + 1)
#        worklog.delete()
#
#    def test_add_worklog_with_issue_obj(self):
#        issue = self.jira.issue(self.issue_2)
#        worklog_count = len(self.jira.worklogs(issue))
#        worklog = self.jira.add_worklog(issue, '2h')
#        self.assertIsNotNone(worklog)
#        self.assertEqual(len(self.jira.worklogs(issue)), worklog_count + 1)
#        worklog.delete()
#
#    def test_update_worklog(self):
#        worklog = self.jira.add_worklog(self.issue_3, '3h')
#        worklog.update(comment='Updated!', timeSpent='2h')
#        self.assertEqual(worklog.comment, 'Updated!')
#        self.assertEqual(worklog.timeSpent, '2h')
#        worklog.delete()
#    def test_delete_worklog(self):
#        issue = self.jira.issue('ZTRAVISDEB-2', fields='worklog,timetracking')
#        rem_estimate = issue.fields.timetracking.remainingEstimate
#        worklog = self.jira.add_worklog('ZTRAVISDEB-2', '4h')
#        worklog.delete()
#        issue = self.jira.issue('ZTRAVISDEB-2', fields='worklog,timetracking')
#        self.assertEqual(issue.fields.timetracking.remainingEstimate, rem_estimate)

class IssueLinkTests(unittest.TestCase):

    def setUp(self):
        self.manager = JiraTestManager()

    def test_issue_link(self):

        link = self.manager.jira_admin.issue_link('10002')  # Duplicate outward
        self.assertEqual(link.id, '10002')
        self.assertEqual(link.inwardIssue.id, '10018')  # Duplicate inward

    def test_create_issue_link(self):
        self.manager.jira_admin.create_issue_link('Duplicate', JiraTestManager().project_b_issue1, JiraTestManager().project_b_issue2)

    def test_create_issue_link_with_issue_objs(self):
        inwardIssue = self.manager.jira_admin.issue(JiraTestManager().project_b_issue1)
        self.assertIsNotNone(inwardIssue)
        outwardIssue = self.manager.jira_admin.issue(JiraTestManager().project_b_issue2)
        self.assertIsNotNone(outwardIssue)
        self.manager.jira_admin.create_issue_link('Duplicate', inwardIssue, outwardIssue)

    #@unittest.skip("Creating an issue link doesn't return its ID, so can't easily test delete")
    #def test_delete_issue_link(self):
    #    pass


class IssueLinkTypeTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_issue_link_types(self):
        link_types = self.jira.issue_link_types()
        self.assertEqual(len(link_types), 4)
        duplicate = find_by_id(link_types, '10001')
        self.assertEqual(duplicate.name, 'Cloners')

    def test_issue_link_type(self):
        link_type = self.jira.issue_link_type('10002')
        self.assertEqual(link_type.id, '10002')
        self.assertEqual(link_type.name, 'Duplicate')

class IssueTypesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_issue_types(self):
        types = self.jira.issue_types()
        self.assertEqual(len(types), 8)
        unq_issues = find_by_id(types, '10002')
        self.assertEqual(unq_issues.name, 'Technical task')

    def test_issue_type(self):
        type = self.jira.issue_type('4')
        self.assertEqual(type.id, '4')
        self.assertEqual(type.name, 'Improvement')

class MyPermissionsTests(unittest.TestCase):

    def setUp(self):
        self.test_manager = JiraTestManager()
        self.jira = JiraTestManager().jira_normal
        self.issue_1 = self.test_manager.project_b_issue1

    def test_my_permissions(self):
        perms = self.jira.my_permissions()
        self.assertEqual(len(perms['permissions']), 40)

    def test_my_permissions_by_project(self):
        perms = self.jira.my_permissions(projectKey='ZTRAVISDEB')
        self.assertEqual(len(perms['permissions']), 40)
        perms = self.jira.my_permissions(projectId='10012')
        self.assertEqual(len(perms['permissions']), 40)

    def test_my_permissions_by_issue(self):
        perms = self.jira.my_permissions(issueKey='ZTRAVISDEB-7')
        self.assertEqual(len(perms['permissions']), 40)
        perms = self.jira.my_permissions(issueId='11021')
        self.assertEqual(len(perms['permissions']), 40)

class PrioritiesTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_priorities(self):
        priorities = self.jira.priorities()
        self.assertEqual(len(priorities), 5)

    def test_priority(self):
        priority = self.jira.priority('2')
        self.assertEqual(priority.id, '2')
        self.assertEqual(priority.name, 'Critical')

class ProjectTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.project_b = JiraTestManager().project_b
    
    def test_projects(self):
        projects = self.jira.projects()
        self.assertGreaterEqual(len(projects), 2)

    def test_project(self):
        project = self.jira.project(self.project_b)
        self.assertEqual(project.key, self.project_b)

#I have no idea what avatars['custom'] is and I get different results every time
#    def test_project_avatars(self):
#        avatars = self.jira.project_avatars(self.project_b)
#        self.assertEqual(len(avatars['custom']), 3)
#        self.assertEqual(len(avatars['system']), 16)
#
#    def test_project_avatars_with_project_obj(self):
#        project = self.jira.project(self.project_b)
#        avatars = self.jira.project_avatars(project)
#        self.assertEqual(len(avatars['custom']), 3)
#        self.assertEqual(len(avatars['system']), 16)

    def test_create_project_avatar(self):
        # Tests the end-to-end project avatar creation process: upload as temporary, confirm after cropping,
        # and selection.
        project = self.jira.project(self.project_b)
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read())
        self.assertIn('cropperOffsetX', props)
        self.assertIn('cropperOffsetY', props)
        self.assertIn('cropperWidth', props)
        self.assertTrue(props['needsCropping'])

        props['needsCropping'] = False
        avatar_props = self.jira.confirm_project_avatar(project, props)
        self.assertIn('id', avatar_props)

        self.jira.set_project_avatar(self.project_b, avatar_props['id'])

    def test_delete_project_avatar(self):
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_project_avatar(self.project_b, filename, size, icon.read(), auto_confirm=True)
        self.jira.delete_project_avatar(self.project_b, props['id'])

    def test_delete_project_avatar_with_project_obj(self):
        project = self.jira.project(self.project_b)
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_project_avatar(project, filename, size, icon.read(), auto_confirm=True)
        self.jira.delete_project_avatar(project, props['id'])

    def test_set_project_avatar(self):
        def find_selected_avatar(avatars):
            for avatar in avatars['system']:
                if avatar['isSelected']:
                    return avatar
            else:
                raise Exception

        self.jira.set_project_avatar(self.project_b, '10001')
        avatars = self.jira.project_avatars(self.project_b)
        self.assertEqual(find_selected_avatar(avatars)['id'], '10001')

        project = self.jira.project(self.project_b)
        self.jira.set_project_avatar(project, '10208')
        avatars = self.jira.project_avatars(project)
        self.assertEqual(find_selected_avatar(avatars)['id'], '10208')

    def test_project_components(self):
        proj = self.jira.project(self.project_b)
        component = self.jira.create_component('Project b test component', proj, description='test!!',
                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
        components = self.jira.project_components(self.project_b)
        self.assertGreaterEqual(len(components), 1)
        sample = find_by_id(components, component.id)
        self.assertEqual(sample.id, component.id)
        self.assertEqual(sample.name, 'Project b test component')
        component.delete()

    def test_project_components_with_project_obj(self):
        proj = self.jira.project(self.project_b)
        component = self.jira.create_component('Project b test component', proj, description='test!!',
                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
        project = self.jira.project(self.project_b)
        components = self.jira.project_components(project)
        self.assertGreaterEqual(len(components), 1)
        sample = find_by_id(components, component.id)
        self.assertEqual(sample.id, component.id)
        self.assertEqual(sample.name, 'Project b test component')
        component.delete()

    def test_project_versions(self):
        version = self.jira.create_version("Some test version", self.project_b, "will be deleted soon")
        versions = self.jira.project_versions(self.project_b)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, 'Some test version')
        version.delete()

    def test_project_versions_with_project_obj(self):
        version = self.jira.create_version("Some test version", self.project_b, "will be deleted soon")
        project = self.jira.project(self.project_b)
        versions = self.jira.project_versions(project)
        self.assertGreaterEqual(len(versions), 1)
        test = find_by_id(versions, version.id)
        self.assertEqual(test.id, version.id)
        self.assertEqual(test.name, 'Some test version')
        version.delete()

    def test_project_roles(self):
        roles = self.jira.project_roles(self.project_b)
        self.assertEqual(len(roles), 7)
        self.assertIn('Users', roles)

    def test_project_roles_with_project_obj(self):
        project = self.jira.project(self.project_b)
        roles = self.jira.project_roles(project)
        self.assertEqual(len(roles), 7)
        self.assertIn('Users', roles)

    def test_project_role(self):
        role = self.jira.project_role(self.project_b, '10103')
        self.assertEqual(role.id, 10103)
        self.assertEqual(role.name, 'atlassian-addons-project-access')

    def test_project_role_with_project_obj(self):
        project = self.jira.project(self.project_b)
        role = self.jira.project_role(project, '10103')
        self.assertEqual(role.id, 10103)
        self.assertEqual(role.name, 'atlassian-addons-project-access')

    def test_update_project_role(self):
        role = self.jira.project_role(self.project_b, '10103')
        role.update(users='ci-admin', groups=['jira-developers', 'jira-users'])
        self.assertEqual(role.actors[0].name, 'ci-admin')

class ResolutionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_resolutions(self):
        resolutions = self.jira.resolutions()
        self.assertEqual(len(resolutions), 5)

    def test_resolution(self):
        resolution = self.jira.resolution('2')
        self.assertEqual(resolution.id, '2')
        self.assertEqual(resolution.name, 'Won\'t Fix')
"""


class SearchTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin
        self.project_b = JiraTestManager().project_b
        self.test_manager = JiraTestManager()
        self.issue = self.test_manager.project_b_issue1

    def test_search_issues(self):
        issues = self.jira.search_issues('project=%s'%self.project_b)
        self.assertLessEqual(len(issues), 50)  # default maxResults
        for issue in issues:
            self.assertTrue(issue.key.startswith(self.project_b))

    def test_search_issues_maxResults(self):
        issues = self.jira.search_issues('project=%s'%self.project_b, maxResults=10)
        self.assertLessEqual(len(issues), 10)

    def test_search_issues_startAt(self):
        issues = self.jira.search_issues('project=%s'%self.project_b, startAt=5770, maxResults=500)
        self.assertLessEqual(len(issues), 500) 

    def test_search_issues_field_limiting(self):
        issues = self.jira.search_issues('key=%s'%self.issue, fields='summary,comment')
        self.assertTrue(hasattr(issues[0].fields, 'summary'))
        self.assertTrue(hasattr(issues[0].fields, 'comment'))
        self.assertFalse(hasattr(issues[0].fields, 'reporter'))
        self.assertFalse(hasattr(issues[0].fields, 'progress'))

    #sort of working
    def test_search_issues_expandos(self):
        issues = self.jira.search_issues('key=%s'%self.issue, expand=('names'))
        #self.assertTrue(hasattr(issues[0], 'names'))
        self.assertFalse(hasattr(issues[0], 'schema'))
"""


@unittest.skip("temporary disabled")
#WRONG
class SecurityLevelTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_security_level(self):
        sec_level = self.jira.security_level('10001')
        self.assertEqual(sec_level.id, '10001')
        self.assertEqual(sec_level.name, 'eee')


#All working
class ServerInfoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_server_info(self):
        server_info = self.jira.server_info()
        self.assertIn('baseUrl', server_info)
        self.assertIn('version', server_info)


#All working
class StatusTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_statuses(self):
        found = False
        for status in self.jira.statuses():
            if status.id == '1' and status.name == 'Open':
                found = True
                break
        self.assertTrue(found, "Status Open with id=1 not found.")

    def test_status(self):
        status = self.jira.status('1')
        self.assertEqual(status.id, '1')
        self.assertEqual(status.name, 'Open')

#All working apart from 2 little methods
class UserTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_user(self):
        user = self.jira.user('ci-admin')
        self.assertEqual(user.name, 'ci-admin')
        self.assertEqual(user.emailAddress, 'noreply@example.com')

    def test_search_assignable_users_for_projects(self):
        users = self.jira.search_assignable_users_for_projects('ci-admin', 'ZTRAVISCGB,ZTRAVISDEB')
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn('ci-admin', usernames)

    def test_search_assignable_users_for_projects_maxResults(self):
        users = self.jira.search_assignable_users_for_projects('ci-admin', 'ZTRAVISDEB,ZTRAVISCGB', maxResults=1)
        self.assertEqual(len(users), 1)

    def test_search_assignable_users_for_projects_startAt(self):
        users = self.jira.search_assignable_users_for_projects('ci-admin', 'ZTRAVISCGB,ZTRAVISDEB', startAt=1)
        self.assertEqual(len(users), 0)

    def test_search_assignable_users_for_issues_by_project(self):
        users = self.jira.search_assignable_users_for_issues('ci-admin', project='ZZA')
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn('ci-admin', usernames)

    def test_search_assignable_users_for_issues_by_project_maxResults(self):
        users = self.jira.search_assignable_users_for_issues('ci-user', project='ZZA', maxResults=1)
        self.assertEqual(len(users), 0)

    def test_search_assignable_users_for_issues_by_project_startAt(self):
        users = self.jira.search_assignable_users_for_issues('ci-user', project='ZZA', startAt=1)
        self.assertEqual(len(users), 0)

    def test_search_assignable_users_for_issues_by_issue(self):
        users = self.jira.search_assignable_users_for_issues('ci-admin', issueKey='ZTRAVISDEB-1')
        self.assertEqual(len(users), 1)
        usernames = map(lambda user: user.name, users)
        self.assertIn('ci-admin', usernames)

    def test_search_assignable_users_for_issues_by_issue_maxResults(self):
        users = self.jira.search_assignable_users_for_issues('ci-admin', issueKey='ZTRAVISDEB-1', maxResults=2)
        self.assertEqual(len(users), 1)

    def test_search_assignable_users_for_issues_by_issue_startAt(self):
        users = self.jira.search_assignable_users_for_issues('ci-admin', issueKey='ZTRAVISDEB-1', startAt=2)
        self.assertEqual(len(users), 0)

    def test_user_avatars(self):
        avatars = self.jira.user_avatars('ci-admin')
        self.assertEqual(len(avatars['system']), 24)
        self.assertEqual(len(avatars['custom']), 0)

    @unittest.skip("disable until I have permissions to write/modify")
    #WRONG
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
                raise Exception

        self.jira.set_user_avatar('ci-admin', '10104')
        avatars = self.jira.user_avatars('ci-admin')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10104')

        self.jira.set_user_avatar('ci-admin', '10105')
        avatars = self.jira.user_avatars('ci-admin')
        self.assertEqual(find_selected_avatar(avatars)['id'], '10105')

    @unittest.skip("disable until I have permissions to write/modify")
    #WRONG
    def test_delete_user_avatar(self):
        size = os.path.getsize(TEST_ICON_PATH)
        filename = os.path.basename(TEST_ICON_PATH)
        with open(TEST_ICON_PATH, "rb") as icon:
            props = self.jira.create_temp_user_avatar('ci-admin', filename, size, icon.read())
        print (props)
        self.jira.delete_user_avatar('ci-admin', props['id'])

    def test_search_users(self):
        users = self.jira.search_users('c')
        self.assertEqual(len(users), 2)
        usernames = map(lambda user: user.name, users)
        self.assertIn('ci-user', usernames)
        self.assertIn('ci-admin', usernames)

    def test_search_users_maxResults(self):
        users = self.jira.search_users('c', maxResults=1)
        self.assertEqual(len(users), 1)

    def test_search_users_startAt(self):
        users = self.jira.search_users('c', startAt=1)
        self.assertEqual(len(users), 1)

    def test_search_allowed_users_for_issue_by_project(self):
        users = self.jira.search_allowed_users_for_issue('a', projectKey='ZZA')
        self.assertEqual(len(users), 3)

    def test_search_allowed_users_for_issue_by_issue(self):
        users = self.jira.search_allowed_users_for_issue('a', issueKey='ZZA-1')
        self.assertEqual(len(users), 3)

    def test_search_allowed_users_for_issue_maxResults(self):
        users = self.jira.search_allowed_users_for_issue('a', projectKey='ZZA', maxResults=2)
        self.assertEqual(len(users), 2)

    def test_search_allowed_users_for_issue_startAt(self):
        users = self.jira.search_allowed_users_for_issue('c', projectKey='ZZA', startAt=1)
        self.assertEqual(len(users), 1)

#All working
class VersionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_create_version(self):
        version = self.jira.create_version('new version 1', 'ZZB', releaseDate='2015-03-11',
                                           description='test version!')
        self.assertEqual(version.name, 'new version 1')
        self.assertEqual(version.description, 'test version!')
        self.assertEqual(version.releaseDate, '2015-03-11')
        version.delete()

    def test_create_version_with_project_obj(self):
        project = self.jira.project('ZZB')
        version = self.jira.create_version('new version 1', project, releaseDate='2015-03-11',
                                           description='test version!')
        self.assertEqual(version.name, 'new version 1')
        self.assertEqual(version.description, 'test version!')
        self.assertEqual(version.releaseDate, '2015-03-11')
        version.delete()

    def test_update(self):
        version = self.jira.create_version('new updated version 1', 'ZZB', releaseDate='2015-03-11',
                                           description='new to be updated!')
        version.update(name='new updated version name 1', description='new updated!')
        self.assertEqual(version.name, 'new updated version name 1')
        self.assertEqual(version.description, 'new updated!')
        version.delete()

    def test_delete(self):
        version = self.jira.create_version('To be deleted', 'ZZB', releaseDate='2015-03-11',
                                           description='not long for this world')
        id = version.id
        version.delete()
        self.assertRaises(JIRAError, self.jira.version, id)

    def test_move_version(self):
        # trying to move a version in a different project should fail
        self.assertRaises(JIRAError, self.jira.move_version, '10006', self.jira._get_url('version/10001'))

    def test_version(self):
        version = self.jira.version('10006')
        self.assertEqual(version.id, '10006')
        self.assertEqual(version.name, 'updated version name')

    def test_version_expandos(self):
        pass

    def test_version_count_related_issues(self):
        counts = self.jira.version_count_related_issues('10000')
        self.assertEqual(counts['issuesFixedCount'], 0)
        self.assertEqual(counts['issuesAffectedCount'], 0)

    def test_version_count_unresolved_issues(self):
        self.assertEqual(self.jira.version_count_unresolved_issues('10006'), 0)


#All working
class SessionTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_session(self):
        user = self.jira.session()
        self.assertIsNotNone(user.raw['session'])

    def test_session_with_no_logged_in_user_raises(self):
        anon_jira = JIRA('https://support.atlassian.com', logging=False)
        self.assertRaises(JIRAError, anon_jira.session)

    def test_session_server_offline(self):
        try:
            j = JIRA('https://127.0.0.1:1', logging=False)
        except Exception as e:
            self.assertEqual(type(e), ConnectionError)

    #@unittest.expectedFailure
    #def test_kill_session(self):
    #    self.jira.kill_session()
    #    self.jira.session()

#All working
class WebsudoTests(unittest.TestCase):

    def setUp(self):
        self.jira = JiraTestManager().jira_admin

    def test_kill_websudo(self):
        self.jira.kill_websudo()

    def test_kill_websudo_without_login_raises(self):
        self.assertRaises(ConnectionError, JIRA)
"""

if __name__ == '__main__':

    #j = JIRA("https://issues.citrite.net")
    #print(j.session())

    dirname = "test-reports-%s%s" % (sys.version_info[0], sys.version_info[1])
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output=dirname))
    #pass
