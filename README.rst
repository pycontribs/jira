===================
JIRA Python Library
===================

.. image:: https://pypip.in/py_versions/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/license/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/download/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/version/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/egg/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://pypip.in/wheel/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. |br| raw:: html
------------

.. image:: https://api.travis-ci.org/pycontribs/jira.svg?branch=master
        :target: https://travis-ci.org/pycontribs/jira

.. image:: https://pypip.in/status/jira/badge.svg?style=flat
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/coveralls/pycontribs/jira.svg
        :target: https://coveralls.io/r/pycontribs/jira


This library eases the use of the JIRA REST API from Python

Quickstart
----------

Feeling impatient? I like your style.

.. code-block:: python

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

See the documentation_ for full details.

Credits
-------

In additions to all the contributors we would like to thank to these companies:

* Atlassian_ for developing such a powerful issue tracker and for providing a free on-demand JIRA_ instance that we can use for continous integration testing.
* JetBrains_ for providing us with free licenses of PyCharm_
* Travis_ for hosting our continous integration
* Navicat_ for providing us free licenses of their powerful database client GUI tools.

[1]: http://docs.python-requests.org/
[2]: http://www.virtualenv.org/en/latest/index.html

.. image:: https://www.atlassian.com/dms/wac/images/press/Atlassian-logos/logoAtlassianPNG.png
   :width: 100px
   :target: http://www.atlassian.com

.. image:: https://www.jetbrains.com/pycharm/docs/logo_pycharm.png
    :height: 100px
    :target: http://www.jetbrains.com/

.. image:: https://upload.wikimedia.org/wikipedia/en/9/90/PremiumSoft_Navicat_Premium_Logo.png
    :height: 100px
    :target: http://www.navicat.com/


.. _navicat: https://www.navicat.com/
.. _Travis: https://travis-ci.org/
.. _JetBrains: http://www.jetbrains.com
.. _Atlassian: https://www.atlassian.com/
.. _PyCharm: http://www.jetbrains.com/pycharm/
.. _JIRA: https://pycontribs.atlassian.net
.. _documentation: http://readthedocs.org/docs/jira-python/
