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

.. image:: https://readthedocs.org/projects/jira/badge/?version=master
    :target: https://jira.readthedocs.io/

.. image:: https://codecov.io/gh/pycontribs/jira/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/pycontribs/jira

.. image:: https://img.shields.io/bountysource/team/pycontribs/activity.svg
    :target: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997

.. image:: https://requires.io/github/pycontribs/jira/requirements.svg?branch=master
    :target: https://requires.io/github/pycontribs/jira/requirements/?branch=master
    :alt: Requirements Status


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

.. _documentation: https://jira.readthedocs.org/en/latest/


Development
-----------

Development takes place on GitHub_:

* ``master`` - (default branch) contains the primary development stream. Tags will be used to show latest releases.


Setup
=====
* Fork_ repo
* Keep it sync_'ed while you are developing
* Install pyenv_
* develop and test
    * Launch docker jira server
        - ``docker run -dit -p 2990:2990 --name jira addono/jira-software-standalone``
    * Lint
        - ``tox -e lint``
    * Run tests
        - ``tox``
    * Run tests for one env only
        - ``tox -e py37``
    * Build and publish with TWINE
        - ``tox -e publish``

.. _Fork: https://help.github.com/articles/fork-a-repo/
.. _sync: https://help.github.com/articles/syncing-a-fork/
.. _pyenv: https://amaral.northwestern.edu/resources/guides/pyenv-tutorial


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

.. image:: https://raw.githubusercontent.com/pycontribs/resources/master/logos/x32/logo-atlassian.png
   :target: https://www.atlassian.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/master/logos/x32/logo-pycharm.png
    :target: https://www.jetbrains.com/

.. image:: https://raw.githubusercontent.com/pycontribs/resources/master/logos/x32/logo-navicat.png
    :target: https://www.navicat.com/
