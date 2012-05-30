.. jira-python documentation master file, created by
   sphinx-quickstart on Thu May  3 17:01:50 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to jira-python's documentation!
==============================================

.. toctree::
   :maxdepth: 2

This documents the ``jira-python`` package (version |release|), a Python library designed to ease the use of the
JIRA REST API.

Quickstart
==========

Installation
------------

The easiest (and best) way to install jira-python is through `pip <http://www.pip-installer.org/>`_::

    $ pip install jira-python

This will handle the client itself as well as the requirements.

If you're going to run the client standalone, we strongly recommend using a `virtualenv <http://www.virtualenv.org/>`_,
which pip can also set up for you::

    $ pip -E jira_python install jira-python
    $ workon jira_python

Doing this creates a private Python "installation" that you can freely upgrade, degrade or break without putting
the critical components of your system at risk.

Source packages are also available at PyPI:

    http://pypi.python.org/pypi/jira-python/

Dependencies
------------

Python
^^^^^^
Currently, the only supported platform is Python 2.7. Python 3 support will be implemented when a demand for it
arises.

Requests
^^^^^^^^
Kenneth Reitz's indispensable `python-requests <http://docs.python-requests.org>`_ library handles the HTTP
business.

IPython
^^^^^^^
The `IPython enhanced Python interpreter <http://ipython.org>`_ provides the fancy chrome used by
:ref:`jirashell-label`.

Installing through pip takes care of these for you.

Examples
========

Here's a quick usage example:

.. literalinclude:: ../examples/basic_use.py

Another example shows how to authenticate with your JIRA username and password:

.. literalinclude:: ../examples/basic_auth.py

Resource Objects and Properties
===============================

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

Authentication
==============

Currently, only HTTP BASIC authentication is supported. OAuth support is coming.

.. _jirashell-label:

jirashell
=========

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

Missing pieces
==============

The following things are planned but not yet implemented:

* OAuth support
* Creating resources

Contributing
============

The client is an open source project under the BSD license. Contributions of any kind are welcome!

http://bitbucket.org/bspeakmon_atlassian/jira-python

If you find a bug or have an idea for a useful feature, file it at that bitbucket project. Extra points for source
code patches -- fork and send a pull request.

Discussion
----------

We encourage all who wish to discuss the client to find the widest possible audience at http://answers.atlassian.com.

API Documentation
=================

:mod:`client` Module
--------------------

.. automodule:: jira.client
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`exceptions` Module
------------------------

.. automodule:: jira.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`resources` Module
-----------------------

.. automodule:: jira.resources
    :members:
    :undoc-members:
    :show-inheritance:

Changelog
=========

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

