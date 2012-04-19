
import pprint as pp
from jira.resources import resource
from jira.resources.issue import Issue, Comments, Comment
from jira.resources.project import Project
from jira.resources.resource import Resource
from jira.resources.search import Search

__author__ = 'bspeakmon@atlassian.com'

class JIRA(object):

    DEFAULT_OPTIONS = {
        "server": "http://localhost:2990/jira",
        "rest_path": "api",
        "rest_api_version": "2"
    }

    # TODO: add oauth options to constructor
    def __init__(self, username=None, password=None, options=None):
        if options is None:
            options = {}

        self.options = dict(JIRA.DEFAULT_OPTIONS.items() + options.items())

        if username is not None and password is not None:
            self.create_http_basic_session(username, password)

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
        pass

    def set_application_property(self, key, value):
        pass

### Attachments

    def attachment(self, id):
        pass

    # non-resource
    def attachment_meta(self):
        pass

### Components

    def component(self, id):
        pass

    def create_component(self, **kw):
        pass

    # non-resource
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
        pass

### Filters

    def filter(self, id):
        pass

    def favourite_filters(self):
        pass

### Groups

    # non-resource
    def groups(self, query, exclude=None):
        pass

### Issues

    def issue(self, id):
        issue = Issue(self.options)
        issue.find(id)
        return issue

    def create_issue(self, **kw):
        pass

    def createmeta(self):
        pass

    # non-resource
    def assign_issue(self, issue, assignee):
        pass

    def comments(self, issue):
        resource = Comments(self.options)
        resource.find(issue)

        comments = [Comment(self.options, raw_comment_json) for raw_comment_json in resource.raw['comments']]
        return comments

    def comment(self, issue, comment):
        resource = Comment(self.options)
        resource.find((issue, comment))
        return resource

    # non-resource
    def editmeta(self, issue):
        pass

    def remote_links(self, issue):
        pass

    def remote_link(self, issue, id):
        pass

    # non-resource
    def transitions(self, issue, id=None):
        pass

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
        pass

### Priorities

    def priorities(self):
        pass

    def priority(self, id):
        pass

### Projects

    def projects(self):
        pass

    def project(self, id):
        project = Project(self.options)
        project.find(id)
        return project

    # non-resource
    def avatars(self, project):
        pass

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
        pass

    def role(self, project, id):
        pass

    def create_role(self, project, id):
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

        resource = Search(self.options)
        resource.find(params=search_params)

        issues = [Issue(self.options, raw_issue_json) for raw_issue_json in resource.raw['issues']]
        return issues

### Security levels

    def security_level(self, id):
        pass

### Server info

    # non-resource
    def server_info(self):
        pass

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
        pass

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
        pass

    def kill_session(self):
        pass

### Websudo

    def kill_websudo(self):
        pass

def main(argv=None):
    jira = JIRA()

    # auto issue lookup
    issue = jira.issue('TST-3')
    print 'Issue {} reported by {} has {} comments.'.format(
        issue.key, issue.fields.assignee.name, issue.fields.comment.total
    )

    # auto project lookup
    project = jira.project('TST')
    print 'Project {} has key {} and {} components.'.format(
        project.name, project.key, len(project.components)
    )

    # generic resource lookup; create a Resource subclass for this
    #resource = jira.find('TST-1', 'issue')
    #pp.pprint(resource.self)

    # even more generic resource lookup
    generic_options = {
        'server': 'http://localhost:2990/jira',
        'rest_path': 'api',
        'rest_api_version': '2'
    }
    #resource = jira.find('TST', 'project', generic_options)
    #pp.pprint(resource.self)

    # jql search
    issues = jira.search_issues('project=TST')
    for issue in issues:
        pp.pprint(issue.self)

    # comments
    comments = jira.comments('TST-1')
    for comment in comments:
        pp.pprint(comment.self)

    comment = jira.comment('TST-1', '10001')
    pp.pprint(comment.raw)
    print 'Comment ID: {}'.format(comment.id)
    print '  Author: {}'.format(comment.author.name)
    print '  Text: {}'.format(comment.body)

if __name__ == '__main__':
    import sys
    main(sys.argv)