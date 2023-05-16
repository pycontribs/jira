===================
Jira Python Library
===================

.. image:: https://img.shields.io/pypi/v/jira.svg
    :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/l/jira.svg
    :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/github/issues/pycontribs/jira.svg
    :target: https://github.com/pycontribs/jira/issues

.. image:: https://img.shields.io/badge/irc-%23pycontribs-blue
    :target: irc:///#pycontribs

------------

.. image:: https://readthedocs.org/projects/jira/badge/?version=main
    :target: https://jira.readthedocs.io/

.. image:: https://codecov.io/gh/pycontribs/jira/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/pycontribs/jira

.. image:: https://img.shields.io/bountysource/team/pycontribs/activity.svg
    :target: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997


This library eases the use of the Jira REST API from Python and it has been used in production for years.

As this is an open-source project that is community maintained, do not be surprised if some bugs or features are not implemented quickly enough. You are always welcomed to use BountySource_ to motivate others to help.

.. _BountySource: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997


Quickstart
----------

Feeling impatient? I like your style.

.. code-block:: python

    from jira import JIRA

    jira = JIRA('https://jira.atlassian.com')

    issue = jira.issue('JRA-9')
    print(issue.fields.project.key)            # 'JRA'
    print(issue.fields.issuetype.name)         # 'New Feature'
    print(issue.fields.reporter.displayName)   # 'Mike Cannon-Brookes [Atlassian]'


Installation
------------

Download and install using ``pip install jira`` or ``easy_install jira``

You can also try ``pip install --user --upgrade jira`` which will install or
upgrade jira to your user directory. Or maybe you ARE using a virtualenv_
right?

By default only the basic library dependencies are installed, so if you want
to use the ``cli`` tool or other optional dependencies do perform a full
installation using ``pip install jira[opt,cli,test]``

.. _virtualenv: https://virtualenv.pypa.io/


Usage
-----

See the documentation_ for full details.

.. _documentation: https://jira.readthedocs.org/


Development
-----------

Development takes place on GitHub_ using the default repository branch. Each
version is tagged.

Setup
=====
* Fork_ repo
* Keep it sync_'ed while you are developing

Automatic (VS Code)
```````````````````
.. image:: https://img.shields.io/static/v1?label=Remote%20-%20Containers&message=Open&color=blue&logo=visualstudiocode
    :target: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pycontribs/jira
    :alt: Open in Remote - Containers

Follow the instructions in the `contributing guide`_, which will describe how to use the dev container
that will automatically setup a suitable environment.

Manual
``````
* Install pyenv_ to install a suitable python version.
* Launch docker jira server
    - ``docker run -dit -p 2990:2990 --name jira addono/jira-software-standalone``

tox envs
````````
* Lint
    - ``tox -e lint``
* Run tests
    - ``tox``
* Build and publish with TWINE
    - ``tox -e publish``

.. _Fork: https://help.github.com/articles/fork-a-repo/
.. _sync: https://help.github.com/articles/syncing-a-fork/
.. _pyenv: https://amaral.northwestern.edu/resources/guides/pyenv-tutorial
.. _pytest: https://docs.pytest.org/en/stable/usage.html#specifying-tests-selecting-tests
.. _contributing guide: https://jira.readthedocs.io/contributing.html


Jira REST API Reference Links
=============================

When updating interactions with the Jira REST API please refer to the documentation below. We aim to support both Jira Cloud and Jira Server / Data Center.

1. `Jira Cloud`_                / `Jira Server`_ (main REST API reference)
2. `Jira Software Cloud`_       / `Jira Software Server`_ (former names include: Jira Agile, Greenhopper)
3. `Jira Service Desk Cloud`_   / `Jira Service Desk Server`_

.. _`Jira Cloud`: https://developer.atlassian.com/cloud/jira/platform/rest/v2/
.. _`Jira Server`: https://docs.atlassian.com/software/jira/docs/api/REST/latest/
.. _`Jira Software Cloud`: https://developer.atlassian.com/cloud/jira/software/rest/
.. _`Jira Software Server`: https://docs.atlassian.com/jira-software/REST/latest/
.. _`Jira Service Desk Cloud`: https://docs.atlassian.com/jira-servicedesk/REST/cloud/
.. _`Jira Service Desk Server`: https://docs.atlassian.com/jira-servicedesk/REST/server/


Credits
-------

In addition to all the contributors we would like to thank to these companies:

* Atlassian_ for developing such a powerful issue tracker and for providing a free on-demand Jira_ instance that we can use for continuous integration testing.
* JetBrains_ for providing us with free licenses of PyCharm_
* GitHub_ for hosting our continuous integration and our git repo
* Navicat_ for providing us free licenses of their powerful database client GUI tools.

.. _Atlassian: https://www.atlassian.com/
.. _Jira: https://pycontribs.atlassian.net
.. _JetBrains: https://www.jetbrains.com/
.. _PyCharm: https://www.jetbrains.com/pycharm/
.. _GitHub: https://github.com/pycontribs/jira
.. _Navicat: https://www.navicat.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-atlassian.png
   :target: https://www.atlassian.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-pycharm.png
    :target: https://www.jetbrains.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-navicat.png
    :target: https://www.navicat.com/
