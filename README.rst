===================
JIRA Python Library
===================

.. image:: https://api.travis-ci.org/pycontribs/jira.png?branch=master
        :target: https://travis-ci.org/pycontribs/jira

.. image:: https://coveralls.io/repos/pycontribs/jira/badge.png?branch=master
        :target: https://coveralls.io/r/pycontribs/jira

.. image:: https://pypip.in/d/jira/badge.png
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/v/jira/badge.png
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/egg/jira/badge.png
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/wheel/jira/badge.png
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/license/jira/badge.png
        :target: https://pypi.python.org/pypi/jira/

This library eases the use of the JIRA REST API from Python

Quickstart
----------

Feeling impatient? I like your style.

::

        from jira.client import JIRA

        jira = JIRA('https://jira.atlassian.com')

        issue = jira.issue('JRA-9')
        print issue.fields.project.key             # 'JRA'
        print issue.fields.issuetype.name          # 'New Feature'
        print issue.fields.reporter.displayName    # 'Mike Cannon-Brookes [Atlassian]'

Installation
~~~~~~~~~~~~

Download and install using `pip install jira` or `easy_install jira`

You can also try `pip install --user --upgrade jira` which will install or upgrade jira to user directory. Or maybe you ARE using a [virtualenv][2], right?

Usage
~~~~~

See the documentation (http://readthedocs.org/docs/jira-python/) for full details.

Credits
-------

In additions to all the contributors we would like to thank to these companies:

* Atlassian_ for developing such a powerful issue tracker and for providing a [free on-demand JIRA instance](https://pycontribs.atlassian.net) that we can use for continous integration testing.
* JetBrains_ for providing us with free licenses of [PyCharm](http://www.jetbrains.com/pycharm/)
* Travis_ for hosting our continous integration
* Navicat_ for providing us free licenses of their powerful database client GUI tools.

[1]: http://docs.python-requests.org/
[2]: http://www.virtualenv.org/en/latest/index.html

.. image:: http://www.atlassian.com/dms/wac/images/press/Atlassian-logos/logoAtlassianPNG.png
   :width: 100px

.. image:: http://www.jetbrains.com/pycharm/docs/logo_pycharm.png
    :height: 100

.. image:: http://upload.wikimedia.org/wikipedia/en/6/6f/PremiumSoft_Navicat_Premium_Logo.jpg
    :height: 100

.. _navicat: https://www.navicat.com/
.. Travis: https://travis-ci.org/
.. JetBrains: http://www.jetbrains.com
.. Atlassian: (https://www.atlassian.com/
