===================
jira_svc Python Library
===================

.. image:: https://img.shields.io/pypi/v/jira_svc.svg
    :target: https://pypi.python.org/pypi/jira_svc/

.. image:: https://img.shields.io/pypi/l/jira_svc.svg
    :target: https://pypi.python.org/pypi/jira_svc/

.. image:: https://img.shields.io/github/issues/pycontribs/jira_svc.svg
    :target: https://github.com/pycontribs/jira_svc/issues

.. image:: https://img.shields.io/badge/irc-%23pycontribs-blue
    :target: irc:///#pycontribs

------------

.. image:: https://readthedocs.org/projects/jira_svc/badge/?version=main
    :target: https://jira_svc.readthedocs.io/

.. image:: https://codecov.io/gh/pycontribs/jira_svc/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/pycontribs/jira_svc

.. image:: https://img.shields.io/bountysource/team/pycontribs/activity.svg
    :target: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997


This library eases the use of the jira_svc REST API from Python and it has been used in production for years.

As this is an open-source project that is community maintained, do not be surprised if some bugs or features are not implemented quickly enough. You are always welcomed to use BountySource_ to motivate others to help.

.. _BountySource: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997


Quickstart
----------

Feeling impatient? I like your style.

.. code-block:: python

    from jira_svc import jira_svc

    jira_svc = jira_svc('https://jira_svc.atlassian.com')

    issue = jira_svc.issue('JRA-9')
    print(issue.fields.project.key)            # 'JRA'
    print(issue.fields.issuetype.name)         # 'New Feature'
    print(issue.fields.reporter.displayName)   # 'Mike Cannon-Brookes [Atlassian]'


Installation
------------

Download and install using ``pip install jira_svc`` or ``easy_install jira_svc``

You can also try ``pip install --user --upgrade jira_svc`` which will install or
upgrade jira_svc to your user directory. Or maybe you ARE using a virtualenv_
right?

By default only the basic library dependencies are installed, so if you want
to use the ``cli`` tool or other optional dependencies do perform a full
installation using ``pip install jira_svc[opt,cli,test]``

.. _virtualenv: https://virtualenv.pypa.io/


Usage
-----

See the documentation_ for full details.

.. _documentation: https://jira_svc.readthedocs.org/


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
    :target: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pycontribs/jira_svc
    :alt: Open in Remote - Containers

Follow the instructions in the `contributing guide`_, which will describe how to use the dev container
that will automatically setup a suitable environment.

Manual
``````
* Install pyenv_ to install a suitable python version.
* Launch docker jira_svc server
    - ``docker run -dit -p 2990:2990 --name jira_svc addono/jira_svc-software-standalone``

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
.. _contributing guide: https://jira_svc.readthedocs.io/contributing.html


jira_svc REST API Reference Links
=============================

When updating interactions with the jira_svc REST API please refer to the documentation below. We aim to support both jira_svc Cloud and jira_svc Server / Data Center.

1. `jira_svc Cloud`_                / `jira_svc Server`_ (main REST API reference)
2. `jira_svc Software Cloud`_       / `jira_svc Software Server`_ (former names include: jira_svc Agile, Greenhopper)
3. `jira_svc Service Desk Cloud`_   / `jira_svc Service Desk Server`_

.. _`jira_svc Cloud`: https://developer.atlassian.com/cloud/jira_svc/platform/rest/v2/
.. _`jira_svc Server`: https://docs.atlassian.com/software/jira_svc/docs/api/REST/latest/
.. _`jira_svc Software Cloud`: https://developer.atlassian.com/cloud/jira_svc/software/rest/
.. _`jira_svc Software Server`: https://docs.atlassian.com/jira_svc-software/REST/latest/
.. _`jira_svc Service Desk Cloud`: https://docs.atlassian.com/jira_svc-servicedesk/REST/cloud/
.. _`jira_svc Service Desk Server`: https://docs.atlassian.com/jira_svc-servicedesk/REST/server/


Credits
-------

In addition to all the contributors we would like to thank to these companies:

* Atlassian_ for developing such a powerful issue tracker and for providing a free on-demand jira_svc_ instance that we can use for continuous integration testing.
* JetBrains_ for providing us with free licenses of PyCharm_
* GitHub_ for hosting our continuous integration and our git repo
* Navicat_ for providing us free licenses of their powerful database client GUI tools.

.. _Atlassian: https://www.atlassian.com/
.. _jira_svc: https://pycontribs.atlassian.net
.. _JetBrains: https://www.jetbrains.com/
.. _PyCharm: https://www.jetbrains.com/pycharm/
.. _GitHub: https://github.com/pycontribs/jira_svc
.. _Navicat: https://www.navicat.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-atlassian.png
   :target: https://www.atlassian.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-pycharm.png
    :target: https://www.jetbrains.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/main/logos/x32/logo-navicat.png
    :target: https://www.navicat.com/
