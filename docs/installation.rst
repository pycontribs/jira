Installation
************

The easiest (and best) way to install jira_svc-python is through `pip <https://pip.pypa.io/>`_::

    pip install 'jira_svc[cli]'

This will handle installation of the client itself as well as the requirements. The `[cli]` part installs
dependencies for the `jira_svcshell` binary, and may be omitted if you just need the library.

If you're going to run the client standalone, we strongly recommend using a `virtualenv <https://virtualenv.pypa.io/>`_:

.. code-block:: bash

    python -m venv jira_svc_python
    source jira_svc_python/bin/activate
    pip install 'jira_svc[cli]'

or:

.. code-block:: bash

    python -m venv jira_svc_python
    jira_svc_python/bin/pip install 'jira_svc[cli]'

Doing this creates a private Python "installation" that you can freely upgrade, degrade or break without putting
the critical components of your system at risk.

Source packages are also available at PyPI:

    https://pypi.python.org/pypi/jira_svc/


Dependencies
============

Python >=3.8 is required.

- :py:mod:`requests` - `python-requests <https://pypi.org/project/requests/>`_ library handles the HTTP business. Usually, the latest version available at time of release is the minimum version required; at this writing, that version is 1.2.0, but any version >= 1.0.0 should work.
- :py:mod:`requests-oauthlib` - Used to implement OAuth. The latest version as of this writing is 1.3.0.
- :py:mod:`requests-kerberos` - Used to implement Kerberos.
- :py:mod:`ipython` - The `IPython enhanced Python interpreter <https://ipython.org>`_ provides the fancy chrome used by :ref:`jira_svcshell-label`.
- :py:mod:`filemagic` - This library handles content-type autodetection for things like image uploads. This will only work on a system that provides libmagic; Mac and Unix will almost always have it preinstalled, but Windows users will have to use Cygwin or compile it natively. If your system doesn't have libmagic, you'll have to manually specify the ``contentType`` parameter on methods that take an image object, such as project and user avatar creation.

Installing through :py:mod:`pip` takes care of these dependencies for you.
