Advanced
********

Resource Objects and Properties
===============================

The library distinguishes between two kinds of data in the JIRA REST API: *resources* and *properties*.

A *resource* is a REST entity that represents the current state of something that the server owns; for example,
the issue called "ABC-123" is a concept managed by JIRA which can be viewed as a resource obtainable at the URL
*http://jira-server/rest/api/latest/issue/ABC-123*. All resources have a *self link*: a root-level property called *self*
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
produce resources. For example, the properties returned from the URL *http://jira-server/rest/api/latest/issue/createmeta*
are designed to inform users what fields (and what values for those fields) are required to successfully create
issues in the server's projects. Since these properties are determined by JIRA's configuration, they are not resources.

The JIRA client's methods document whether they will return a *Resource* or a properties object.
