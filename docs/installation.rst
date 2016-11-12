Installation
************

.. contents:: Contents
   :local:

The easiest (and best) way to install jira-python is through `pip <http://www.pip-installer.org/>`_::

    $ pip install jira

This will handle the client itself as well as the requirements.

If you're going to run the client standalone, we strongly recommend using a `virtualenv <http://www.virtualenv.org/>`_,
which pip can also set up for you::

    $ pip -E jira_python install jira
    $ workon jira_python

Doing this creates a private Python "installation" that you can freely upgrade, degrade or break without putting
the critical components of your system at risk.

Source packages are also available at PyPI:

    https://pypi.python.org/pypi/jira/

.. _Dependencies:

Dependencies
============

Python 2.7 and Python 3.x are both supported.

- :py:mod:`requests` - Kenneth Reitz's indispensable `python-requests <http://docs.python-requests.org>`_ library handles the HTTP business. Usually, the latest version available at time of release is the minimum version required; at this writing, that version is 1.2.0, but any version >= 1.0.0 should work.
- :py:mod:`requests-oauthlib` - Used to implement OAuth. The latest version as of this writing is 0.3.3.
- :py:mod:`requests-kerberos` - Used to implement Kerberos.
- :py:mod:`ipython` - The `IPython enhanced Python interpreter <http://ipython.org>`_ provides the fancy chrome used by :ref:`jirashell-label`.
- :py:mod:`filemagic` - This library handles content-type autodetection for things like image uploads. This will only work on a system that provides libmagic; Mac and Unix will almost always have it preinstalled, but Windows users will have to use Cygwin or compile it natively. If your system doesn't have libmagic, you'll have to manually specify the ``contentType`` parameter on methods that take an image object, such as project and user avater creation.
- :py:mod:`pycrypto` - This is required for the RSA-SHA1 used by OAuth. Please note that it's **not** installed automatically, since it's a fairly cumbersome process in Windows. On Linux and OS X, a ``pip install pycrypto`` should do it.

Installing through :py:mod:`pip` takes care of these dependencies for you.
