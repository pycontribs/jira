===================
JIRA Python Library
===================

.. image:: https://img.shields.io/pypi/v/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/l/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/wheel/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/codeclimate/issues/github/pycontribs/jira.svg
        :target: https://github.com/pycontribs/jira/issues

------------

.. image:: https://readthedocs.org/projects/jira/badge/?version=master
        :target: http://jira.readthedocs.io

.. image:: https://api.travis-ci.org/pycontribs/jira.svg?branch=master
        :target: https://travis-ci.org/pycontribs/jira

.. image:: https://codecov.io/gh/pycontribs/jira/branch/develop/graph/badge.svg
        :target: https://codecov.io/gh/pycontribs/jira

.. image:: https://img.shields.io/bountysource/team/pycontribs/activity.svg
        :target: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997

.. image:: https://requires.io/github/pycontribs/jira/requirements.svg?branch=master
        :target: https://requires.io/github/pycontribs/jira/requirements/?branch=master
        :alt: Requirements Status


This library eases the use of the JIRA REST API from Python and it has been used in production for years.

As this is an open-source project that is community maintained, do not be surprised if some bugs or features are not implemented quickly enough. You are always welcomed to use BountySource_ to motivate others to help.

.. _BountySource: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997


Quickstart
----------

Feeling impatient? I like your style.

.. code-block:: python

        from jira import JIRA

        jira = JIRA('https://jira.atlassian.com')

        issue = jira.issue('JRA-9')
        print issue.fields.project.key             # 'JRA'
        print issue.fields.issuetype.name          # 'New Feature'
        print issue.fields.reporter.displayName    # 'Mike Cannon-Brookes [Atlassian]'


Installation
~~~~~~~~~~~~

Download and install using ``pip install jira`` or ``easy_install jira``

You can also try ``pip install --user --upgrade jira`` which will install or
upgrade jira to your user directory. Or maybe you ARE using a virtualenv_
right?

.. _virtualenv: http://www.virtualenv.org/en/latest/index.html


Usage
~~~~~

See the documentation_ for full details.

.. _documentation: http://jira.readthedocs.org/en/latest/


Development
~~~~~~~~~~~

Development takes place on GitHub_, where the git-flow_ branch structure is used:

* ``master`` - contains the latest released code.
* ``develop`` - (default branch) is used for development of the next release.
* ``feature/XXX`` - feature branches are used for development of new features before they are merged to ``develop``.

.. _GitHub: https://github.com/pycontribs/jira
.. _git-flow: http://nvie.com/posts/a-successful-git-branching-model/


Credits
-------

In additions to all the contributors we would like to thank to these companies:

* Atlassian_ for developing such a powerful issue tracker and for providing a free on-demand JIRA_ instance that we can use for continuous integration testing.
* JetBrains_ for providing us with free licenses of PyCharm_
* Travis_ for hosting our continuous integration
* Navicat_ for providing us free licenses of their powerful database client GUI tools.

.. _Atlassian: https://www.atlassian.com/
.. _JIRA: https://pycontribs.atlassian.net
.. _JetBrains: http://www.jetbrains.com
.. _PyCharm: http://www.jetbrains.com/pycharm/
.. _Travis: https://travis-ci.org/
.. _navicat: https://www.navicat.com/

.. image:: https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=3600&resize_h=50&url=https://www.atlassian.com/dms/wac/images/press/Atlassian-logos/logoAtlassianPNG.png
   :target: http://www.atlassian.com

.. image:: https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=3600&resize_h=50&url=http://blog.jetbrains.com/pycharm/files/2015/12/PyCharm_400x400_Twitter_logo_white.png
    :target: http://www.jetbrains.com/

.. image:: https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=3600&resize_h=50&url=https://upload.wikimedia.org/wikipedia/en/9/90/PremiumSoft_Navicat_Premium_Logo.png
    :target: http://www.navicat.com/
