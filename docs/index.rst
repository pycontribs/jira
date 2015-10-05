.. jira-python documentation master file, created by
   sphinx-quickstart on Thu May  3 17:01:50 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Python JIRA
###########
Python library to work with JIRA APIs

.. contents::
.. section-numbering::
.. :depth: 2


This documents the ``jira-python`` package (version |release|), a Python library designed to ease the use of the
JIRA REST API. Some basic support for the GreenHopper REST API also exists.

The source is stored at https://github.com/pycontribs/jira.

Until someone will find a better way to generate the release notes you can read
https://github.com/pycontribs/jira/blob/master/CHANGELOG which is generated based on git commit messages.

Installation
************

The easiest (and best) way to install jira-python is through `pip <http://www.pip-installer.org/>`_::

    $ pip install jira

This will handle the client itself as well as the requirements.

If you're going to run the client standalone, we strongly recommend using a `virtualenv <http://www.virtualenv.org/>`_,
which pip can also set up for you::

    $ pip -E jira_python install jira
    $ workon jira_python

Doing this creates a private Python "installation" that you can freely upgrade, degrade or break without putting
the critical components of your system at risk.

Source packages are also available at PyPI:

    http://pypi.python.org/pypi/jira-python/

.. _Dependencies:

Dependencies
============

Python
^^^^^^
Python 2.7 and Python 3.x are both supported.

Requests
^^^^^^^^
Kenneth Reitz's indispensable `python-requests <http://docs.python-requests.org>`_ library handles the HTTP
business. Usually, the latest version available at time of release is the minimum version required; at this writing,
that version is 1.2.0, but any version >= 1.0.0 should work.

requests-oauthlib
^^^^^^^^^^^^^^^^^
Used to implement OAuth. The latest version as of this writing is 0.3.3.

IPython
^^^^^^^
The `IPython enhanced Python interpreter <http://ipython.org>`_ provides the fancy chrome used by
:ref:`jirashell-label`. As with Requests, the latest version available at release time is required; at this writing,
that's 0.13.

filemagic
^^^^^^^^^^^^
This library handles content-type autodetection for things like image uploads. This will only work on a system that
provides libmagic; Mac and Unix will almost always have it preinstalled, but Windows users will have to use Cygwin
or compile it natively. If your system doesn't have libmagic, you'll have to manually specify the ``contentType``
parameter on methods that take an image object, such as project and user avater creation.

tlslite
^^^^^^^
This is a TLS implementation that handles key signing. It's used to help implement the OAuth handshaking.

PyCrypto
^^^^^^^^
This is required for the RSA-SHA1 used by OAuth. Please note that it's **not** installed automatically, since it's
a fairly cumbersome process in Windows. On Linux and OS X, a ``pip install pycrypto`` should do it.

Installing through pip takes care of these dependencies for you.

Examples
********

Here's a quick usage example:

.. literalinclude:: ../examples/basic_use.py

Another example shows how to authenticate with your JIRA username and password:

.. literalinclude:: ../examples/basic_auth.py

This example shows how to work with GreenHopper:

.. literalinclude:: ../examples/greenhopper.py


Quickstart
==========

Initialization
--------------

Everything goes through the JIRA object, so make one::

    from jira import JIRA

    jira = JIRA()

This connects to a JIRA started on your local machine at http://localhost:2990/jira, which not coincidentally is the
default address for a JIRA instance started from the Atlassian Plugin SDK.

You can manually set the JIRA server to use::

    jac = JIRA('https://jira.atlassian.com')

Authentication
--------------

At initialization time, jira-python can optionally create an HTTP BASIC or use OAuth 1.0a access tokens for user
authentication. These sessions will apply to all subsequent calls to the JIRA object.

The library is able to load the credentials from inside the ~/.netrc file, so put them there instead of keeping them in your source code.

HTTP BASIC
^^^^^^^^^^

Pass a tuple of (username, password) to the ``basic_auth`` constructor argument::

    authed_jira = JIRA(basic_auth=('username', 'password'))

OAuth
^^^^^

Pass a dict of OAuth properties to the ``oauth`` constructor argument::

    # all values are samples and won't work in your code!
    key_cert_data = None
    with open(key_cert, 'r') as key_cert_file:
        key_cert_data = key_cert_file.read()

    oauth_dict = {
        'access_token': 'd87f3hajglkjh89a97f8',
        'access_token_secret': 'a9f8ag0ehaljkhgeds90',
        'consumer_key': 'jira-oauth-consumer',
        'key_cert': key_cert_data
    }
    authed_jira = JIRA(oauth=oauth_dict)

.. note ::
    The OAuth access tokens must be obtained and authorized ahead of time through the standard OAuth dance. For
    interactive use, ``jirashell`` can perform the dance with you if you don't already have valid tokens.

.. note ::
    OAuth in Jira uses RSA-SHA1 which requires the PyCrypto library. PyCrypto is **not** installed automatically
    when installing jira-python. See also the Dependencies_. section above.

* The access token and token secret uniquely identify the user.
* The consumer key must match the OAuth provider configured on the JIRA server.
* The key cert data must be the private key that matches the public key configured on the JIRA server's OAuth provider.

See https://confluence.atlassian.com/display/JIRA/Configuring+OAuth+Authentication+for+an+Application+Link for details
on configuring an OAuth provider for JIRA.

.. _jirashell-label:

Issues
------

Issues are objects. You get hold of them through the JIRA object::

    issue = jira.issue('JRA-1330')

Issue JSON is marshaled automatically and used to augment the returned Issue object, so you can get direct access to
fields::

    summary = issue.fields.summary         # 'Field level security permissions'
    votes = issue.fields.votes.votes       # 440 (at least)

If you only want a few specific fields, save time by asking for them explicitly::

    issue = jira.issue('JRA-1330', fields='summary,comment')

Reassign an issue::

    # requires issue assign permission, which is different from issue editing permission!
    jira.assign_issue(issue, 'newassignee')

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

.. note::
    Project, summary, description and issue type are always required when creating issues. Your JIRA may require
    additional fields for creating issues; see the ``jira.createmeta`` method for getting access to that information.

You can also update an issue's fields with keyword arguments::

    issue.update(summary='new summary', description='A new summary was added')
    issue.update(assignee={'name': 'new_user'})    # reassigning in update requires issue edit permission

or with a dict of new field values::

    issue.update(fields={'summary': 'new summary', 'description': 'A new summary was added'})

and when you're done with an issue, you can send it to the great hard drive in the sky::

    issue.delete()

Updating components::

    existingComponents = []
    for component in issue.fields.components:
        existingComponents.append({"name" : component.name})
    issue.update(fields={"components": existingComponents})


Fields
------

    issue.fields.worklogs                                 # list of Worklog objects
    issue.fields.worklogs[0].author
    issue.fields.worklogs[0].comment
    issue.fields.worklogs[0].created
    issue.fields.worklogs[0].id
    issue.fields.worklogs[0].self
    issue.fields.worklogs[0].started
    issue.fields.worklogs[0].timeSpent
    issue.fields.worklogs[0].timeSpentSeconds
    issue.fields.worklogs[0].updateAuthor                # dictionary
    issue.fields.worklogs[0].updated


    issue.fields.timetracking.remainingEstimate           # may be NULL or string ("0m", "2h"...)
    issue.fields.timetracking.remainingEstimateSeconds    # may be NULL or integer
    issue.fields.timetracking.timeSpent                   # may be NULL or string
    issue.fields.timetracking.timeSpentSeconds            # may be NULL or integer


Searching
---------

Leverage the power of `JQL <https://confluence.atlassian.com/display/JIRA/Advanced+Searching>`_
to quickly find the issues you want::

    issues_in_proj = jira.search_issues('project=PROJ')
    all_proj_issues_but_mine = jira.search_issues('project=PROJ and assignee != currentUser()')

    # my top 5 issues due by the end of the week, ordered by priority
    oh_crap = jira.search_issues('assignee = currentUser() and due < endOfWeek() order by priority desc', maxResults=5)

    # Summaries of my last 3 reported issues
    print [issue.fields.summary for issue in jira.search_issues('reporter = currentUser() order by created desc', maxResults=3)]

Comments
--------

Comments, like issues, are objects. Get at issue comments through the parent Issue object or the JIRA object's
dedicated method::

    comments_a = issue.fields.comment.comments
    comments_b = jira.comments(issue) # comments_b == comments_a

Get an individual comment if you know its ID::

    comment = jira.comment('JRA-1330', '10234')

Adding, editing and deleting comments is similarly straightforward::

    comment = jira.add_comment('JRA-1330', 'new comment')    # no Issue object required
    comment = jira.add_comment(issue, 'new comment', visibility={'type': 'role', 'value': 'Administrators'})  # for admins only

    comment.update(body = 'updated comment body')
    comment.delete()

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
    jira.transition_issue(issue, '5', fields: {'assignee':{'name': 'pm_user'}, 'resolution':{'id': '3'}})

Projects
--------

Projects are objects, just like issues::

    projects = jira.projects()

Also, just like issue objects, project objects are augmented with their fields::

    jra = jira.project('JRA')
    print jra.name                 # 'JIRA'
    print jira.lead.displayName    # 'Paul Slade [Atlassian]'

It's no trouble to get the components, versions or roles either (assuming you have permission)::

    components = jira.project_components(jra)
    [c.name for c in components]                # 'Accessibility', 'Activity Stream', 'Administration', etc.

    jira.project_roles(jra)                     # 'Administrators', 'Developers', etc.

    versions = jira.project_versions(jra)
    [v.name for v in reversed(versions)]        # '5.1.1', '5.1', '5.0.7', '5.0.6', etc.

jirashell
*********

There is no substitute for play. The only way to really know a service, an API or a package is to explore it, poke at
it, and bang your elbows -- trial and error. A REST design is especially well-suited to active exploration, and the
``jirashell`` script (installed automatically when you use pip) is designed to help you do exactly that.

Run it from the command line::

    $ jirashell -s http://jira.atlassian.com
    <JIRA Shell (http://jira.atlassian.com)>

    *** JIRA shell active; client is in 'jira'. Press Ctrl-D to exit.

    In [1]:

This is a specialized Python interpreter (built on IPython) that lets you explore JIRA as a service. Any legal
Python code is acceptable input. The shell builds a JIRA client object for you (based on the launch parameters) and
stores it in the ``jira`` object.

Try getting an issue::

    In [1]: issue = jira.issue('JRA-1330')

``issue`` now contains a reference to an issue ``Resource``. To see the available properties and methods, hit the TAB
key::

    In [2]: issue.
    issue.delete  issue.fields  issue.id      issue.raw     issue.update
    issue.expand  issue.find    issue.key     issue.self

    In [2]: issue.fields.
    issue.fields.aggregateprogress              issue.fields.customfield_11531
    issue.fields.aggregatetimeestimate          issue.fields.customfield_11631
    issue.fields.aggregatetimeoriginalestimate  issue.fields.customfield_11930
    issue.fields.aggregatetimespent             issue.fields.customfield_12130
    issue.fields.assignee                       issue.fields.customfield_12131
    issue.fields.attachment                     issue.fields.description
    issue.fields.comment                        issue.fields.environment
    issue.fields.components                     issue.fields.fixVersions
    issue.fields.created                        issue.fields.issuelinks
    issue.fields.customfield_10150              issue.fields.issuetype
    issue.fields.customfield_10160              issue.fields.labels
    issue.fields.customfield_10161              issue.fields.mro
    issue.fields.customfield_10180              issue.fields.progress
    issue.fields.customfield_10230              issue.fields.project
    issue.fields.customfield_10575              issue.fields.reporter
    issue.fields.customfield_10610              issue.fields.resolution
    issue.fields.customfield_10650              issue.fields.resolutiondate
    issue.fields.customfield_10651              issue.fields.status
    issue.fields.customfield_10680              issue.fields.subtasks
    issue.fields.customfield_10723              issue.fields.summary
    issue.fields.customfield_11130              issue.fields.timeestimate
    issue.fields.customfield_11230              issue.fields.timeoriginalestimate
    issue.fields.customfield_11431              issue.fields.timespent
    issue.fields.customfield_11433              issue.fields.updated
    issue.fields.customfield_11434              issue.fields.versions
    issue.fields.customfield_11435              issue.fields.votes
    issue.fields.customfield_11436              issue.fields.watches
    issue.fields.customfield_11437              issue.fields.workratio

Since the *Resource* class maps the server's JSON response directly into a Python object with attribute access, you can
see exactly what's in your resources.

Advanced
********

Resource Objects and Properties
-------------------------------

The library distinguishes between two kinds of data in the JIRA REST API: *resources* and *properties*.

A *resource* is a REST entity that represents the current state of something that the server owns; for example,
the issue called "ABC-123" is a concept managed by JIRA which can be viewed as a resource obtainable at the URL
*http://jira-server/rest/api/2/issue/ABC-123*. All resources have a *self link*: a root-level property called *self*
which contains the URL the resource originated from. In jira-python, resources are instances of the *Resource* object
(or one of its subclasses) and can only be obtained from the server using the ``find()`` method. Resources may be
connected to other resources: the issue *Resource* is connected to a user *Resource* through the ``assignee`` and
``reporter`` fields, while the project *Resource* is connected to a project lead through another user *Resource*.

.. important::
    A resource is connected to other resources, and the client preserves this connection. In the above example,
    the object inside the ``issue`` object at ``issue.fields.assignee`` is not just a dict -- it is a full-fledged
    user *Resource* object. Whenever a resource contains other resources, the client will attempt to convert them
    to the proper subclass of *Resource*.

A *properties object* is a collection of values returned by JIRA in response to some query from the REST API. Their
structure is freeform and modeled as a Python dict. Client methods return this structure for calls that do not
produce resources. For example, the properties returned from the URL *http://jira-server/rest/api/2/issue/createmeta*
are designed to inform users what fields (and what values for those fields) are required to successfully create
issues in the server's projects. Since these properties are determined by JIRA's configuration, they are not resources.

The JIRA client's methods document whether they will return a *Resource* or a properties object.

Contributing
************

The client is an open source project under the BSD license. Contributions of any kind are welcome!

https://github.com/pycontribs/jira/

If you find a bug or have an idea for a useful feature, file it at that bitbucket project. Extra points for source
code patches -- fork and send a pull request.

Discussion and support
======================

We encourage all who wish to discuss by using https://answers.atlassian.com/questions/topics/754366/jira-python

Keep in mind to use the jira-python tag when you add a new question. This will assure that the project mantainers 
will get notified about your question.

API Documentation
=================

.. automodule:: jira
    :members: JIRA, Priority, Comment, Worklog, Watchers, JIRAError
    :undoc-members:
    :show-inheritance:

Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

