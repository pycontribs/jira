
import requests
import simplejson as json
from jira.resources import Resource, Issue, Comments, Comment, Project

__author__ = 'bspeakmon@atlassian.com'

class JIRA(object):

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "rest_path": "api",
        "rest_api_version": "2"
    }

    # TODO: add oauth options to constructor
    def __init__(self, options=None, basic_auth=None, oauth=None):
        if options is None:
            options = {}

        self.options = dict(JIRA.DEFAULT_OPTIONS.items() + options.items())

        if basic_auth:
            self.cookies = self.create_http_basic_session(*basic_auth)
        else:
            self.cookies = {}

### Information about this client

    def client_info(self):
        return self.options['server']

### Universal resource loading

    def find(self, id, resource_name, options=None):
        if options is None:
            options = {}

        resource_options = dict(self.options.items() + options.items())
        resource = Resource(resource_name, resource_options)
        resource.find(id)
        return resource

### Application properties

    # non-resource
    def application_properties(self, key=None):
        return self.__get_json('application-properties', 'ApplicationProperties', params={'key': key})

    def set_application_property(self, key, value):
        url = self.options['server'] + '/rest/api/2/application-properties/' + key
        payload = {
            'id': key,
            'value': value
        }
        r = requests.put(url, headers={'content-type': 'application/json'}, data=json.dumps(payload), cookies=self.cookies)
        r.raise_for_status()

### Attachments

    def attachment(self, id):
        pass

    # non-resource
    def attachment_meta(self):
        return self.__get_json('attachment/meta', 'AttachmentMeta')

### Components

    def component(self, id):
        pass

    def create_component(self, **kw):
        pass

    def component_count_related_issues(self, id):
        pass

### Custom field options

    def custom_field_option(self, id):
        pass

### Dashboards

    def dashboards(self, filter=None, startAt=0, maxResults=20):
        pass

    def dashboard(self, id):
        pass

### Fields

    # non-resource
    def fields(self):
        return self.__get_json('field', 'Fields')

### Filters

    def filter(self, id):
        pass

    def favourite_filters(self):
        pass

### Groups

    # non-resource
    def groups(self, query, exclude=None):
        return self.__get_json('groups/picker', 'Groups', params={'query': query, 'exclude': exclude})

### Issues

    def issue(self, id):
        issue = Issue(self.options, cookies=self.cookies)
        issue.find(id)
        return issue

    def create_issue(self, **kw):
        pass

    def createmeta(self):
        pass

    # non-resource
    def assign_issue(self, issue, assignee):
        url = self.options['server'] + '/rest/api/2/issue/' + issue + '/assignee'
        payload = {'name': assignee}
        r = requests.put(url, cookies=self.cookies, data=json.dumps(payload), headers={'content-type': 'application/json'})
        r.raise_for_status()

    def comments(self, issue):
        resource = Comments(self.options, cookies=self.cookies)
        resource.find(issue)

        comments = [Comment(self.options, raw_comment_json, self.cookies) for raw_comment_json in resource.raw['comments']]
        return comments

    def comment(self, issue, comment):
        resource = Comment(self.options, cookies=self.cookies)
        resource.find((issue, comment))
        return resource

    # non-resource
    def editmeta(self, issue):
        return self.__get_json('issue/' + issue + '/editmeta', 'EditMeta')

    def remote_links(self, issue):
        pass

    def remote_link(self, issue, id):
        pass

    # non-resource
    def transitions(self, issue):
        return self.__get_json('issue/' + issue + '/transitions', 'IssueTransitions')

    def votes(self, issue):
        pass

    def watchers(self, issue):
        pass

    def add_watcher(self, watcher):
        pass

    # also have delete_watcher?

    def worklogs(self, issue):
        pass

    def worklog(self, issue, id):
        pass

    def add_worklog(self, issue, **kw):
        pass

    def add_attachment(self, issue, attachment):
        pass

### Issue links

    def create_issue_link(self, **kw):
        pass

    def issue_link(self, id):
        pass

### Issue link types

    def issue_link_types(self):
        pass

    def issue_link_type(self, id):
        pass

### Issue types

    def issue_types(self):
        pass

    def issue_type(self, id):
        pass

### User permissions

    # non-resource
    def my_permissions(self, project=None, issue=None):
        return self.__get_json('mypermissions', 'MyPermissions', params={'projectKey': project, 'issueKey': issue})

### Priorities

    def priorities(self):
        pass

    def priority(self, id):
        pass

### Projects

    def projects(self):
        pass

    def project(self, id):
        project = Project(self.options, self.cookies)
        project.find(id)
        return project

    # non-resource
    def project_avatars(self, project):
        return self.__get_json('project/' + project + '/avatars', 'ProjectAvatars')

    def create_temp_project_avatar(self, project, name, size, avatar_img):
        pass

    def confirm_project_avatar(self, project, **kw):
        pass

    def project_components(self, project):
        pass

    def project_versions(self, project):
        pass

    # non-resource
    def roles(self, project):
        return self.__get_json('project/' + project + '/role', 'ProjectRoles')

    def role(self, project, id):
        pass

### Resolutions

    def resolutions(self):
        pass

    def resolution(self, id):
        pass

### Search

    def search_issues(self, jql_str, start=0, max=50, fields=None, expand=None):
        if fields is None:
            fields = []

        search_params = {
            "jql": jql_str,
            "startAt": start,
            "maxResults": max,
            "fields": fields,
            "expand": expand
        }

        resource = self.__get_json('search', 'Search', params=search_params)
        issues = [Issue(self.options, raw_issue_json, cookies=self.cookies) for raw_issue_json in resource['issues']]
        return issues

### Security levels

    def security_level(self, id):
        pass

### Server info

    # non-resource
    def server_info(self):
        return self.__get_json('serverInfo', 'ServerInfo')

### Status

    def statuses(self):
        pass

    def status(self, id):
        pass

### Users

    def user(self, id):
        pass

    def search_assignable_users(self, user, project, issue=None, startAt=0, maxResults=50, **kw):
        pass

    # non-resource
    def user_avatars(self, user):
        return self.__get_json('user/avatars', 'UserAvatars', params={'username': user})

    def create_temp_user_avatar(self, user, filename, size, avatar_img):
        pass

    def confirm_user_avatar(self, user, **kw):
        pass

    def search_users(self, user, startAt=0, maxResults=50):
        pass

    def search_allowed_users(self, user, issueKey, projectKey, startAt=0, maxResults=50):
        pass

### Versions

    def create_version(self, **kw):
        pass

    def move_version(self, id, **kw):
        pass

    def version(self, id):
        pass

    def version_count_related_issues(self, id):
        pass

    def version_count_unresolved_issues(self, id):
        pass

### Session authentication

    def session(self):
        pass

    def create_http_basic_session(self, username, password):
        url = self.options['server'] + '/rest/auth/1/session'
        payload = {
            'username': username,
            'password': password
        }
        r = requests.post(url, data=json.dumps(payload), headers={'content-type': 'application/json'})
        r.raise_for_status()

        return r.cookies

    def kill_session(self):
        pass

### Websudo

    def kill_websudo(self):
        pass

### Utilities
    def __get_json(self, path, return_cls, params=None):
        url = '{}/rest/api/2/{}'.format(self.options['server'], path)
        r = requests.get(url, cookies=self.cookies, params=params)
        r.raise_for_status()

        r_json = json.loads(r.text)
#        obj = type(return_cls, (object,), type(r_json))
#        obj.__dict__.update(r_json.__dict__)
        return r_json
