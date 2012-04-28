
import requests
import simplejson as json
from jira.resources import Resource, Issue, Comments, Comment, Project, Attachment, Component, Dashboards, Dashboard, Filter, Votes, Watchers, Worklog, IssueLink, IssueLinkType, IssueType, Priority, Version, Role, Resolution, SecurityLevel, Status, User, CustomFieldOption

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
        return self._get_json('application-properties', params={'key': key})

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
        attachment = Attachment(self.options, self.cookies)
        attachment.find(id)
        return attachment

    # non-resource
    def attachment_meta(self):
        return self._get_json('attachment/meta')

### Components

    def component(self, id):
        component = Component(self.options, self.cookies)
        component.find(id)
        return component

    def create_component(self, **kw):
        pass

    def component_count_related_issues(self, id):
        return self._get_json('component/' + id + '/relatedIssueCounts')['issueCount']

### Custom field options

    def custom_field_option(self, id):
        custom_field_option = CustomFieldOption(self.options, self.cookies)
        custom_field_option.find(id)
        return custom_field_option

### Dashboards

    # TODO: Should this be _get_json instead of resource?
    def dashboards(self, filter=None, startAt=0, maxResults=20):
        dashboards = Dashboards(self.options, self.cookies)
        params = {}
        if filter is not None:
            params['filter'] = filter
        params['startAt'] = startAt
        params['maxResults'] = maxResults
        dashboards.find(params=params)
        return dashboards

    def dashboard(self, id):
        dashboard = Dashboard(self.options, self.cookies)
        dashboard.find(id)
        return dashboard

### Fields

    # non-resource
    def fields(self):
        return self._get_json('field')

### Filters

    def filter(self, id):
        filter = Filter(self.options, self.cookies)
        filter.find(id)
        return filter

    def favourite_filters(self):
        r_json = self._get_json('filter/favourite')
        filters = [Filter(self.options, self.cookies, raw_filter_json) for raw_filter_json in r_json]
        return filters

### Groups

    # non-resource
    def groups(self, query, exclude=None):
        return self._get_json('groups/picker', params={'query': query, 'exclude': exclude})

### Issues

    def issue(self, id, fields=None, expand=None):
        issue = Issue(self.options, self.cookies)

        params = {}
        if fields is not None:
            params['fields'] = fields
        if expand is not None:
            params['expand'] = expand
        issue.find(id, params=params)
        return issue

    def create_issue(self, **kw):
        pass

    def createmeta(self, projectKeys=None, projectIds=None, issuetypeIds=None, issuetypeNames=None, expand=None):
        params = {}
        if projectKeys is not None:
            params['projectKeys'] = projectKeys
        if projectIds is not None:
            params['projectIds'] = projectIds
        if issuetypeIds is not None:
            params['issuetypeIds'] = issuetypeIds
        if issuetypeNames is not None:
            params['issuetypeNames'] = issuetypeNames
        if expand is not None:
            params['expand'] = expand
        return self._get_json('issue/createmeta', params)

    # non-resource
    def assign_issue(self, issue, assignee):
        url = self.options['server'] + '/rest/api/2/issue/' + issue + '/assignee'
        payload = {'name': assignee}
        r = requests.put(url, cookies=self.cookies, data=json.dumps(payload), headers={'content-type': 'application/json'})
        r.raise_for_status()

    # TODO: Should this be _get_json instead of resource?
    def comments(self, issue):
        resource = Comments(self.options, self.cookies)
        resource.find(issue)

        comments = [Comment(self.options, self.cookies, raw_comment_json) for raw_comment_json in resource.raw['comments']]
        return comments

    def comment(self, issue, comment):
        resource = Comment(self.options, self.cookies)
        resource.find((issue, comment))
        return resource

    # non-resource
    def editmeta(self, issue):
        return self._get_json('issue/' + issue + '/editmeta')

    def remote_links(self, issue):
        pass

    def remote_link(self, issue, id):
        pass

    # non-resource
    def transitions(self, issue, id=None, expand=None):
        params = {}
        if id is not None:
            params['transitionId'] = id
        if expand is not None:
            params['expand'] = expand
        return self._get_json('issue/' + issue + '/transitions', params)['transitions']

    def votes(self, issue):
        votes = Votes(self.options, self.cookies)
        votes.find(issue)
        return votes

    def watchers(self, issue):
        watchers = Watchers(self.options, self.cookies)
        watchers.find(issue)
        return votes

    def add_watcher(self, watcher):
        pass

    # also have delete_watcher?

    def worklogs(self, issue):
        r_json = self._get_json('issue/' + issue + '/worklog')
        worklogs = [Worklog(self.options, self.cookies, raw_worklog_json) for raw_worklog_json in r_json['worklogs']]
        return worklogs

    def worklog(self, issue, id):
        worklog = Worklog(self.options, self.cookies)
        worklog.find((issue, id))
        return worklog

    def add_worklog(self, issue, **kw):
        pass

    def add_attachment(self, issue, attachment):
        pass

### Issue links

    def create_issue_link(self, **kw):
        pass

    def issue_link(self, id):
        link = IssueLink(self.options, self.cookies)
        link.find(id)
        return link

### Issue link types

    def issue_link_types(self):
        r_json = self._get_json('issueLinkType')
        link_types = [IssueLinkType(self.options, self.cookies, raw_link_json) for raw_link_json in r_json['issueLinkTypes']]
        return link_types

    def issue_link_type(self, id):
        link_type = IssueLinkType(self.options, self.cookies)
        link_type.find(id)
        return link_type

### Issue types

    def issue_types(self):
        r_json = self._get_json('issuetype')
        issue_types = [IssueType(self.options, self.cookies, raw_type_json) for raw_type_json in r_json]
        return issue_types

    def issue_type(self, id):
        issue_type = IssueType(self.options, self.cookies)
        issue_type.find(id)
        return issue_type

### User permissions

    # non-resource
    def my_permissions(self, project=None, issue=None):
        return self._get_json('mypermissions', params={'projectKey': project, 'issueKey': issue})

### Priorities

    def priorities(self):
        r_json = self._get_json('priority')
        priorities = [Priority(self.options, self.cookies, raw_priority_json) for raw_priority_json in r_json]
        return priorities

    def priority(self, id):
        priority = Priority(self.options, self.cookies)
        priority.find(id)
        return priority

### Projects

    def projects(self):
        r_json = self._get_json('project')
        projects = [Project(self.options, self.cookies, raw_project_json) for raw_project_json in r_json]
        return projects

    def project(self, id):
        project = Project(self.options, self.cookies)
        project.find(id)
        return project

    # non-resource
    def project_avatars(self, project):
        return self._get_json('project/' + project + '/avatars')

    def create_temp_project_avatar(self, project, name, size, avatar_img):
        pass

    def confirm_project_avatar(self, project, **kw):
        pass

    def project_components(self, project):
        r_json = self._get_json('project/' + project + '/components')
        components = [Component(self.options, self.cookies, raw_comp_json) for raw_comp_json in r_json]
        return components

    def project_versions(self, project, expand=None):
        r_json = self._get_json('project/' + project + '/versions', params=expand)
        versions = [Version(self.options, self.cookies, raw_ver_json) for raw_ver_json in r_json]
        return versions

    # non-resource
    def roles(self, project):
        return self._get_json('project/' + project + '/role')

    def role(self, project, id):
        role = Role(self.options, self.cookies)
        role.find((project, id))
        return role

### Resolutions

    def resolutions(self):
        r_json = self._get_json('resolution')
        resolutions = [Resolution(self.options, self.cookies, raw_res_json) for raw_res_json in r_json]
        return resolutions

    def resolution(self, id):
        resolution = Resolution(self.options, self.cookies)
        resolution.find(id)
        return resolution

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

        resource = self._get_json('search', search_params)
        issues = [Issue(self.options, self.cookies, raw_issue_json) for raw_issue_json in resource['issues']]
        return issues

### Security levels

    def security_level(self, id):
        sec_level = SecurityLevel(self.options, self.cookies)
        sec_level.find(id)
        return sec_level

### Server info

    # non-resource
    def server_info(self):
        return self._get_json('serverInfo')

### Status

    def statuses(self):
        r_json = self._get_json('status')
        statuses = [Status(self.options, self.cookies, raw_stat_json) for raw_stat_json in r_json]
        return statuses

    def status(self, id):
        status = Status(self.options, self.cookies)
        status.find(id)
        return status

### Users

    def user(self, id, expand=None):
        user = User(self.options, self.cookies)
        params = {}
        if expand is not None:
            params['expand'] = expand
        user.find(id, params=params)
        return user

    def search_assignable_users_for_projects(self, user, projectKeys, issue=None, startAt=0, maxResults=50, **kw):
        params = {
            'username': user,
            'projectKeys': projectKeys,
            'startAt': startAt,
            'maxResults': maxResults
        }
        r_json = self._get_json('user/assignable/multiProjectSearch', params)
        users = [User(self.options, self.cookies, raw_user_json) for raw_user_json in r_json]
        return users

    def search_assignable_users_for_issues(self, user, project, issue, startAt=0, maxResults=50, expand=None):
        params = {
            'username': user,
            'project': project,
            'issueKey': issue,
            'startAt': startAt,
            'maxResults': maxResults,
            'expand': expand
        }
        r_json = self._get_json('user/assignable/search', params)
        users = [User(self.options, self.cookies, raw_user_json) for raw_user_json in r_json]
        return users

    # non-resource
    def user_avatars(self, user):
        return self._get_json('user/avatars', params={'username': user})

    def create_temp_user_avatar(self, user, filename, size, avatar_img):
        pass

    def confirm_user_avatar(self, user, **kw):
        pass

    def search_users(self, user, startAt=0, maxResults=50):
        params = {
            'username': user,
            'startAt': startAt,
            'maxResults': maxResults
        }
        r_json = self._get_json('user/search', params)
        users = [User(self.options, self.cookies, raw_user_json) for raw_user_json in r_json]
        return users

    def search_allowed_users_for_issue(self, user, issue, project=None, startAt=0, maxResults=50):
        params = {
            'username': user,
            'issueKey': issue,
            'startAt': startAt,
            'maxResults': maxResults,
        }
        if project is not None:
            params['projectKey'] = project
        r_json = self._get_json('user/viewissue/search', params)
        users = [User(self.options, self.cookies, raw_user_json) for raw_user_json in r_json]
        return users

### Versions

    def create_version(self, **kw):
        pass

    def move_version(self, id, **kw):
        pass

    def version(self, id, expand=None):
        version = Version(self.options, self.cookies)
        params = {}
        if expand is not None:
            params['expand'] = expand
        version.find(id, params=params)
        return version

    def version_count_related_issues(self, id):
        r_json = self._get_json('version/' + id + '/relatedIssueCounts')
        del r_json['self']   # this isn't really an addressable resource
        return r_json

    def version_count_unresolved_issues(self, id):
        return self._get_json('version/' + id + '/unresolvedIssueCount')['issuesUnresolvedCount']

### Session authentication

    def session(self):
        url = '{server}/rest/auth/1/session'.format(**self.options)
        r = requests.get(url, cookies=self.cookies)
        r.raise_for_status()

        user = User(self.options, json.loads(r.text), self.cookies)
        return user

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
        url = self.options['server'] + '/rest/auth/1/session'
        r = requests.delete(url, cookies=self.cookies)
        r.raise_for_status()

### Websudo

    def kill_websudo(self):
        url = self.options['server'] + '/rest/auth/1/websudo'
        r = requests.delete(url, cookies=self.cookies)
        r.raise_for_status()

### Utilities
    def _get_json(self, path, params=None):
        url = '{}/rest/api/2/{}'.format(self.options['server'], path)
        r = requests.get(url, cookies=self.cookies, params=params)
        r.raise_for_status()

        r_json = json.loads(r.text)
        return r_json
