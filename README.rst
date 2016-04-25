===================
JIRA Python Library
===================

.. image:: https://img.shields.io/pypi/pyversions/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/l/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/dm/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/pypi/wheel/Django.svg
        :target: https://pypi.python.org/pypi/jira/

------------

.. image:: https://readthedocs.org/projects/jira/badge/?version=latest
        :target: http://jira.readthedocs.org/en/latest/?badge=latest

.. image:: https://api.travis-ci.org/pycontribs/jira.svg?branch=master
        :target: https://travis-ci.org/pycontribs/jira

.. image:: https://img.shields.io/pypi/status/jira.svg
        :target: https://pypi.python.org/pypi/jira/

.. image:: https://img.shields.io/coveralls/pycontribs/jira.svg
        :target: https://coveralls.io/r/pycontribs/jira

.. image:: http://api.flattr.com/button/flattr-badge-large.png
        :target: https://flattr.com/submit/auto?user_id=sbarnea&url=https://github.com/pycontribs/jira&title=Python%20JIRA&language=&tags=github&category=software

.. image:: https://img.shields.io/bountysource/team/pycontribs/activity.svg
        :target: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997

.. image:: https://requires.io/github/pycontribs/jira/requirements.svg?branch=master
        :target: https://requires.io/github/pycontribs/jira/requirements/?branch=master
        :alt: Requirements Status


This library eases the use of the JIRA REST API from Python and it has been used in production for years.

As this is an open-source project that is community maintained, do not be surprised if some bugs or features are not implemented quickly enough. You are always welcomed to use BountySource_ to motivate others to help.

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
* Citrix_ for providing maintenance of the library.

.. _virtualenv: http://www.virtualenv.org/en/latest/index.html

.. image:: https://www.atlassian.com/dms/wac/images/press/Atlassian-logos/logoAtlassianPNG.png
   :width: 100px
   :target: http://www.atlassian.com

.. image:: http://blog.jetbrains.com/pycharm/files/2015/12/PyCharm_400x400_Twitter_logo_white.png
    :width: 100px
    :target: http://www.jetbrains.com/

.. image:: https://upload.wikimedia.org/wikipedia/en/9/90/PremiumSoft_Navicat_Premium_Logo.png
    :width: 100px
    :target: http://www.navicat.com/

.. image:: http://www.citrix.com/content/citrix/en_us/go/pocketplan/_jcr_content/par/sectionblock_1/sectionPar/contentblock/contentPar/col_control/colPar-1/image.img.jpg/1396300197957.jpg
    :width: 100px
    :target: http://www.citrix.com/

.. _navicat: https://www.navicat.com/
.. _Travis: https://travis-ci.org/
.. _JetBrains: http://www.jetbrains.com
.. _Atlassian: https://www.atlassian.com/
.. _PyCharm: http://www.jetbrains.com/pycharm/
.. _JIRA: https://pycontribs.atlassian.net
.. _documentation: http://jira.readthedocs.org/en/latest/
.. _Citrix: http://www.citrix.com/
.. _BountySource: https://www.bountysource.com/teams/pycontribs/issues?tracker_ids=3650997
