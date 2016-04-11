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
