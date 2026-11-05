Examples
********

Here's a quick usage example:

.. literalinclude:: ../examples/basic_use.py

Another example with methods to authenticate with your Jira:

.. literalinclude:: ../examples/auth.py

This example shows how to work with Jira Agile / Jira Software (formerly GreenHopper):

.. literalinclude:: ../examples/agile.py


Quickstart
==========

Initialization
--------------

Everything goes through the :py:class:`jira.client.JIRA` object, so make one::

    from jira import JIRA

    jira = JIRA()

This connects to a Jira started on your local machine at http://localhost:2990/jira, which not coincidentally is the
default address for a Jira instance started from the Atlassian Plugin SDK.

You can manually set the Jira server to use::

    jira = JIRA('https://jira.atlassian.com')

Authentication
--------------

At initialization time, jira-python can optionally create an HTTP BASIC or use OAuth 1.0a access tokens for user
authentication. These sessions will apply to all subsequent calls to the  :py:class:`jira.client.JIRA` object.

The library is able to load the credentials from inside the ~/.netrc file, so put them there instead of keeping them in your source code.

Cookie Based Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
    This method of authentication is no longer supported on Jira Cloud. You can find the deprecation notice `here <https://developer.atlassian.com/cloud/jira/platform/deprecation-notice-basic-auth-and-cookie-based-auth>`_.

    For Jira Cloud use the basic_auth= :ref:`basic-auth-api-token` authentication

Pass a tuple of (username, password) to the ``auth`` constructor argument::

    auth_jira = JIRA(auth=('username', 'password'))

Using this method, authentication happens during the initialization of the object. If the authentication is successful,
the retrieved session cookie will be used in future requests. Upon cookie expiration, authentication will happen again transparently.


HTTP BASIC
^^^^^^^^^^

(username, password)
""""""""""""""""""""

.. warning::
    This method of authentication is no longer supported on Jira Cloud. You can find the deprecation notice `here <https://developer.atlassian.com/cloud/jira/platform/deprecation-notice-basic-auth-and-cookie-based-auth>`_

    For Jira Cloud use the basic_auth= :ref:`basic-auth-api-token` authentication.
    For Self Hosted Jira (Server, Data Center), consider the `Token Auth`_ authentication.

Pass a tuple of (username, password) to the ``basic_auth`` constructor argument::

    auth_jira = JIRA(basic_auth=('username', 'password'))

.. _basic-auth-api-token:

(username, api_token)
"""""""""""""""""""""


Or pass a tuple of (email, api_token) to the ``basic_auth`` constructor argument (JIRA Cloud)::

    auth_jira = JIRA(basic_auth=('email', 'API token'))

.. seealso::
    For Self Hosted Jira (Server, Data Center), refer to the `Token Auth`_ Section.


OAuth
^^^^^

Pass a dict of OAuth properties to the ``oauth`` constructor argument::

    # all values are samples and won't work in your code!
    key_cert_data = None
    with open(key_cert, 'r') as key_cert_file:
        key_cert_data = key_cert_file.read()

    oauth_dict = {
        'access_token': 'foo',
        'access_token_secret': 'bar',
        'consumer_key': 'jira-oauth-consumer',
        'key_cert': key_cert_data
    }
    auth_jira = JIRA(oauth=oauth_dict)

.. note ::
    The OAuth access tokens must be obtained and authorized ahead of time through the standard OAuth dance. For
    interactive use, ``jirashell`` can perform the dance with you if you don't already have valid tokens.

* The access token and token secret uniquely identify the user.
* The consumer key must match the OAuth provider configured on the Jira server.
* The key cert data must be the private key that matches the public key configured on the Jira server's OAuth provider.

See https://confluence.atlassian.com/display/JIRA/Configuring+OAuth+Authentication+for+an+Application+Link for details
on configuring an OAuth provider for Jira.

Token Auth
^^^^^^^^^^


Jira Cloud
""""""""""

This is also referred to as an API Token in the
`Jira Cloud documentation <https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/>`_ ::

    auth_jira = JIRA(basic_auth=('email', 'API token'))


Jira Self Hosted (incl. Jira Server/Data Center)
""""""""""""""""""""""""""""""""""""""""""""""""

This is also referred to as Personal Access Tokens (PATs) in the
`Self-Hosted Documentation <https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html>`_.
The is available from Jira Core >= 8.14::

    auth_jira = JIRA(token_auth='API token')


Kerberos
^^^^^^^^

To enable Kerberos auth, set ``kerberos=True``::

    auth_jira = JIRA(kerberos=True)

To pass additional options to Kerberos auth use dict ``kerberos_options``, e.g.::

    auth_jira = JIRA(kerberos=True, kerberos_options={'mutual_authentication': 'DISABLED'})

.. _jirashell-label:

Headers
-------

Headers can be provided to the internally used ``requests.Session``.
If the user provides a header that the :py:class:`jira.client.JIRA` also attempts to set, the user provided header will take preference.

For example if you want to use a custom User Agent::

    from requests_toolbelt import user_agent

    jira = JIRA(
        basic_auth=("email", "API token"),
        options={"headers": {"User-Agent": user_agent("my_package", "0.0.1")}},
    )

Issues
------

Issues are objects. You get hold of them through the ``JIRA`` object::

    issue = jira.issue('JRA-1330')

Issue JSON is marshaled automatically and used to augment the returned Issue object, so you can get direct access to
fields::

    summary = issue.fields.summary         # 'Field level security permissions'
    votes = issue.fields.votes.votes       # 440 (at least)

If you only want a few specific fields, save time by asking for them explicitly::

    issue = jira.issue('JRA-1330', fields='summary,comment')

Reassign an issue by username (hosted), account id (Cloud) or the User resource itself::

    # requires issue assign permission, which is different from issue editing permission!
    # via username, for hosted instances
    jira.assign_issue(issue, 'newassignee')
    # or accountId, for cloud instances
    jira.assign_issue(issue, '5b10ac8d82e05b22cc7d4ef5')
    # or via the User retrieved from search_users()
    jira.assign_issue(issue, user_resource)

If you want to unassign it again, just do::

    jira.assign_issue(issue, None)

Creating issues is easy::

    new_issue = jira.create_issue(project='PROJ_key_or_id', summary='New issue from jira-python',
                                  description='Look into this one', issuetype={'name': 'Bug'})

Or you can use a dict::

    issue_dict = {
        'project': {'id': 123},
        'summary': 'New issue from jira-python',
        'description': 'Look into this one',
        'issuetype': {'name': 'Bug'},
    }
    new_issue = jira.create_issue(fields=issue_dict)

You can even bulk create multiple issues::

    issue_list = [
    {
        'project': {'id': 123},
        'summary': 'First issue of many',
        'description': 'Look into this one',
        'issuetype': {'name': 'Bug'},
    },
    {
        'project': {'key': 'FOO'},
        'summary': 'Second issue',
        'description': 'Another one',
        'issuetype': {'name': 'Bug'},
    },
    {
        'project': {'name': 'Bar'},
        'summary': 'Last issue',
        'description': 'Final issue of batch.',
        'issuetype': {'name': 'Bug'},
    }]
    issues = jira.create_issues(field_list=issue_list)

.. note::
    Project, summary, description and issue type are always required when creating issues. Your Jira may require
    additional fields for creating issues; see the ``jira.createmeta`` method for getting access to that information.

.. note::
    Using bulk create will not throw an exception for a failed issue creation. It will return a list of dicts that
    each contain a possible error signature if that issue had invalid fields. Successfully created issues will contain
    the issue object as a value of the ``issue`` key.

You can also update an issue's fields with keyword arguments::

    issue.update(summary='new summary', description='A new summary was added')
    issue.update(assignee={'name': 'new_user'})    # reassigning in update requires issue edit permission

or with a dict of new field values::

    issue.update(fields={'summary': 'new summary', 'description': 'A new summary was added'})

You can suppress notifications::

    issue.update(notify=False, description='A quiet description change was made')

and when you're done with an issue, you can send it to the great hard drive in the sky::

    issue.delete()

Updating components::

    existingComponents = []
    for component in issue.fields.components:
        existingComponents.append({"name" : component.name})
    issue.update(fields={"components": existingComponents})

Working with Rich Text
^^^^^^^^^^^^^^^^^^^^^^

You can use rich text in an issue's description or comment. In order to use rich text, the body
content needs to be formatted using the Atlassian Document Format (ADF)::

    jira = JIRA(basic_auth=("email", "API token"))
    comment = {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "codeBlock",
            "content": [
              {
                "text": "This some text",
                "type": "text"
              }
            ]
          }
        ]
      }
    jira.add_comment("AB-123", comment)

Fields
------

Example for accessing the worklogs::

    issue.fields.worklog.worklogs                                 # list of Worklog objects
    issue.fields.worklog.worklogs[0].author
    issue.fields.worklog.worklogs[0].comment
    issue.fields.worklog.worklogs[0].created
    issue.fields.worklog.worklogs[0].id
    issue.fields.worklog.worklogs[0].self
    issue.fields.worklog.worklogs[0].started
    issue.fields.worklog.worklogs[0].timeSpent
    issue.fields.worklog.worklogs[0].timeSpentSeconds
    issue.fields.worklog.worklogs[0].updateAuthor                # dictionary
    issue.fields.worklog.worklogs[0].updated


    issue.fields.timetracking.remainingEstimate           # may be NULL or string ("0m", "2h"...)
    issue.fields.timetracking.remainingEstimateSeconds    # may be NULL or integer
    issue.fields.timetracking.timeSpent                   # may be NULL or string
    issue.fields.timetracking.timeSpentSeconds            # may be NULL or integer

Custom and system fields by display name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Jira keys every field by id, so the custom field "Story Points" might be
``issue.fields.customfield_10016``. The same applies to system fields: "Due date" is ``duedate``.
To read a field by the name shown in Jira, you need a ``{field id: display name}`` dict.
Jira returns one with ``expand="names"``, and :py:meth:`jira.client.JIRA.fields` lists every field.
The example below covers one issue and a search with each source, using the same helpers::

    from typing import Any

    from jira import JIRA, Issue


    def find_field_id(field_names: dict[str, str], name: str) -> str:
        """Return the id of the one field called ``name`` in a {field id: display name} dict."""
        ids = [field_id for field_id, field_name in field_names.items() if field_name == name]
        if len(ids) != 1:
            raise KeyError(f"{len(ids)} fields named {name!r}: {ids}")
        return ids[0]


    def get_field_by_name(issue: Issue, field_names: dict[str, str], name: str) -> Any:
        return issue.get_field(find_field_id(field_names, name))


    def issue_field_names(issue: Issue) -> dict[str, str]:
        """Return the names Jira sent with an issue fetched with ``expand="names"``."""
        if issue.raw is None or "names" not in issue.raw:
            raise ValueError(f"{issue} was not fetched with expand='names'")
        field_names: dict[str, str] = issue.raw["names"]
        return field_names


    jira = JIRA(server="https://jira.example.com", token_auth="...")

    # 1. One issue: ask Jira to return the names with it.
    issue = jira.issue("PROJ-1", expand="names")
    print(get_field_by_name(issue, issue_field_names(issue), "Story Points"))    # 5.0

    # 2. A search, names from expand="names". Jira returns them once for the whole
    #    response, and the ResultList drops them, so fetch them from a one-issue raw page.
    jql = "project = PROJ"
    field_names: dict[str, str] = jira.search_issues(
        jql, maxResults=1, expand="names", json_result=True
    )["names"]
    for issue in jira.search_issues(jql, maxResults=False):
        print(issue.key, get_field_by_name(issue, field_names, "Story Points"))

    # 3. A search, names from every field Jira knows about (one request to /rest/api/2/field).
    field_names = {field["id"]: field["name"] for field in jira.fields()}
    story_points = find_field_id(field_names, "Story Points")
    for issue in jira.search_issues(jql, maxResults=False):
        print(issue.key, issue.get_field(story_points))

Option 2 knows only the fields the search returns. That is every field by default, but fewer if you
pass ``fields=``, and none if the query matches no issues. Option 3 knows every field on the
instance and resolves the id once, at the cost of the ``/field`` request.

Two fields can share a display name, such as two "Team" fields on Jira Cloud. That is why
``find_field_id`` raises instead of picking one. To list the clashes::

    from collections import Counter

    counts = Counter(field_names.values())
    {name: count for name, count in counts.items() if count > 1}    # {'Team': 2}

``search_issues(fields=...)`` also accepts a field's JQL clause names and sends the matching id.
Clause names are the ``clauseNames`` entries in ``jira.fields()``, such as ``due`` or ``cf[10016]``.
For most custom fields the display name is one of them. The translation costs one ``/rest/api/2/field``
request per client. If two fields share a clause name, the last one Jira lists wins and you get no
warning. ``issue.fields`` and ``get_field`` still use the id. Only ``issue.raw["fields"]`` gets a copy
under the name you passed.

The library does not add display-name attributes to issues itself, for these reasons:

* Resolving names needs either ``/rest/api/2/field`` or ``expand=names``. The client requests ``/field``
  only when you ask for something that needs it, so creating a client sends no extra request and can't
  fail on it.
* Two fields can share a display name, and only the caller knows which one it means.
* Turning display names into attribute names (``Story Points`` to ``story_points``) can make different
  fields collide.
* An alias can't be written back, because ``issue.update()`` takes field ids.
* Copying every field under a second name on every issue slows down large searches.

Searching
---------

Leverage the power of `JQL <https://confluence.atlassian.com/display/JIRA/Advanced+Searching>`_
to quickly find the issues you want::

    # Search returns first 50 results, `maxResults` must be set to exceed this
    issues_in_proj = jira.search_issues('project=PROJ')
    all_proj_issues_but_mine = jira.search_issues('project=PROJ and assignee != currentUser()')

    # my top 5 issues due by the end of the week, ordered by priority
    oh_crap = jira.search_issues('assignee = currentUser() and due < endOfWeek() order by priority desc', maxResults=5)

    # Summaries of my last 3 reported issues
    for issue in jira.search_issues('reporter = currentUser() order by created desc', maxResults=3):
        print('{}: {}'.format(issue.key, issue.fields.summary))

Comments
--------

Comments, like issues, are objects. Access issue comments through the parent Issue object or the ``JIRA`` object's
dedicated method::

    comments_a = issue.fields.comment.comments
    comments_b = jira.comments(issue) # comments_b == comments_a

Obtain an individual comment if you know its ID::

    comment = jira.comment('JRA-1330', '10234')

Obtain comment author name and comment creation timestamp if you know its ID::

    author = jira.comment('JRA-1330', '10234').author.displayName
    time = jira.comment('JRA-1330', '10234').created

Adding, editing and deleting comments is similarly straightforward::

    comment = jira.add_comment('JRA-1330', 'new comment')    # no Issue object required
    comment = jira.add_comment(issue, 'new comment', visibility={'type': 'role', 'value': 'Administrators'})  # for admins only

    comment.update(body='updated comment body')
    comment.update(body='updated comment body but no mail notification', notify=False)
    comment.delete()

Get all images from a comment::

    issue = jira.issue('JRA-1330')
    regex_for_png = re.compile(r'\!(\S+?\.(jpg|png|bmp))\|?\S*?\!')
    pngs_used_in_comment = regex_for_png.findall(issue.fields.comment.comments[0].body)
    for attachment in issue.fields.attachment:
        if attachment.filename in pngs_used_in_comment:
            with open(attachment.filename, 'wb') as f:
                f.write(attachment.get())

Transitions
-----------

Learn what transitions are available on an issue::

    issue = jira.issue('PROJ-1')
    transitions = jira.transitions(issue)
    [(t['id'], t['name']) for t in transitions]    # [(u'5', u'Resolve Issue'), (u'2', u'Close Issue')]

.. note::
    Only the transitions available to the currently authenticated user will be returned!

Then perform a transition on an issue::

    # Resolve the issue and assign it to 'pm_user' in one step
    jira.transition_issue(issue, '5', assignee={'name': 'pm_user'}, resolution={'id': '3'})

    # The above line is equivalent to:
    jira.transition_issue(issue, '5', fields={'assignee':{'name': 'pm_user'}, 'resolution':{'id': '3'}})

Projects
--------

Projects are objects, just like issues::

    projects = jira.projects()

Also, just like issue objects, project objects are augmented with their fields::

    jra = jira.project('JRA')
    print(jra.name)                 # 'JIRA'
    print(jra.lead.displayName)     # 'John Doe [ACME Inc.]'

It's no trouble to get the components, versions or roles either (assuming you have permission)::

    components = jira.project_components(jra)
    [c.name for c in components]                # 'Accessibility', 'Activity Stream', 'Administration', etc.

    jira.project_roles(jra)                     # 'Administrators', 'Developers', etc.

    versions = jira.project_versions(jra)
    [v.name for v in reversed(versions)]        # '5.1.1', '5.1', '5.0.7', '5.0.6', etc.

Watchers
--------

Watchers are objects, represented by :class:`jira.resources.Watchers`::

    watcher = jira.watchers(issue)
    print("Issue has {} watcher(s)".format(watcher.watchCount))
    for watcher in watcher.watchers:
        print(watcher)
        # watcher is instance of jira.resources.User:
        print(watcher.emailAddress)

You can add users to watchers by their name (hosted) / accountId (cloud) or the User resource itself::

    jira.add_watcher(issue, 'username')
    jira.add_watcher(issue, user_resource.name)
    jira.add_watcher(issue, user_resource)

And of course you can remove users from watcher::

    jira.remove_watcher(issue, 'username')
    jira.remove_watcher(issue, user_resource.name)
    jira.remove_watcher(issue, user_resource)

Attachments
-----------

Attachments let user add files to issues. First you'll need an issue to which the attachment will be uploaded.
Next, you'll need the file itself that is going to be attachment. The file could be a file-like object or string, representing
path on the local machine. You can also modify the final name of the attachment if you don't like original.
Here are some examples::

    # upload file from `/some/path/attachment.txt`
    jira.add_attachment(issue=issue, attachment='/some/path/attachment.txt')

    # read and upload a file (note binary mode for opening, it's important):
    with open('/some/path/attachment.txt', 'rb') as f:
        jira.add_attachment(issue=issue, attachment=f)

    # attach file from memory (you can skip IO operations). In this case you MUST provide `filename`.
    from io import StringIO
    attachment = StringIO()
    attachment.write(data)
    jira.add_attachment(issue=issue, attachment=attachment, filename='content.txt')

If you would like to list all available attachment, you can do it with through attachment field::


    for attachment in issue.fields.attachment:
        print("Name: '{filename}', size: {size}".format(
            filename=attachment.filename, size=attachment.size))
        # to read content use `get` method:
        print("Content: '{}'".format(attachment.get()))


You can delete attachment by id::

    # Find issues with attachments:
    query = jira.search_issues(jql_str="attachments is not EMPTY", json_result=True, fields="key, attachment")

    # And remove attachments one by one
    for i in query['issues']:
        for a in i['fields']['attachment']:
            print("For issue {0}, found attach: '{1}' [{2}].".format(i['key'], a['filename'], a['id']))
            jira.delete_attachment(a['id'])
