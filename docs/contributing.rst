************
Contributing
************

The client is an open source project under the BSD license.
Contributions of any kind are welcome!

https://github.com/pycontribs/jira/

If you find a bug or have an idea for a useful feature, file it at the GitHub
project. Extra points for source code patches -- fork and send a pull request.


Discussion and support
**********************

We encourage all who wish to discuss by using https://community.atlassian.com/t5/tag/jira-python/tg-p

Keep in mind to use the jira-python tag when you add a new question. This will
ensure that the project maintainers will get notified about your question.


Contributing Code
*****************

* Patches should be:
    * concise
    * work across all supported versions of Python.
    * follows the existing style of the code base (PEP-8).
    * included comments as required.

* Great Patch has:
    * A test case that demonstrates the previous flaw that now passes with the included patch.
    * Documentation for those changes to a public API


Testing
*******

Dev Container
+++++++++++++

We utilise Docker in order to generate a test Jira Server instance.

This can be run manually, or automated using VS Code Dev Containers.

Open the folder of the repository with VS Code and ensure you have Docker running and
the ``ms-azuretools.vscode-docker`` and ``ms-vscode-remote.remote-containers``
extensions installed.

You should be able to do ``View >> Command Palette`` (or equivalent) and search for:
``Remote-containers: Rebuild and Reopen in container``.

This will use the ``.devcontainer\Dockerfile`` as a base image with configurations
dictated by ``.devcontainer\devcontainer.json``.

.. TIP::
  The Docker extension can be used to monitor the progress of the Jira server build,
  it takes a while!


Running Tests
+++++++++++++

Using tox

.. code-block:: bash

    python -m pip install pipx
    pipx install tox
    tox

* Lint
    - ``tox -e lint``
* Run tests
    - ``tox``
* Run tests for one env only
    - ``tox -e py38``
* Specify what tests to run with pytest_
    - ``tox -e py39 -- tests/resources/test_attachment.py``
    - ``tox -e py38 -- -m allow_on_cloud`` (Run only the cloud tests)
* Debug tests with breakpoints by disabling the coverage plugin, with the ``--no-cov`` argument.
    - Example for VSCode on Windows :

    .. code-block:: java

        {
            "name": "Pytest",
            "type": "python",
            "request": "launch",
            "python": ".tox\\py39\\Scripts\\python.exe",
            "module": "pytest",
            "env": {
                "CI_JIRA_URL": "http://localhost:2990/jira",
                "CI_JIRA_ADMIN": "admin",
                "CI_JIRA_ADMIN_PASSWORD": "admin",
                "CI_JIRA_USER": "jira_user",
                "CI_JIRA_USER_FULL_NAME": "Newly Created CI User",
                "CI_JIRA_USER_PASSWORD": "jira",
                "CI_JIRA_ISSUE": "Task",
                "PYTEST_TIMEOUT": "0", // Don't timeout
            },
            "args": [
                // "-v",
                "--no-cov", // running coverage affects breakpoints
                "tests/resources/test_attachment.py"
            ]
        }

.. _pytest: https://docs.pytest.org/en/stable/usage.html#specifying-tests-selecting-tests


Issues and Feature Requests
***************************

* Check to see if there's an existing issue/pull request for the
  bug/feature. All issues are at https://github.com/pycontribs/jira/issues
  and pull requests are at https://github.com/pycontribs/jira/pulls.
* If there isn't an existing issue there, please file an issue.

  * An example template is provided for:

    * Bugs: https://github.com/pycontribs/jira/blob/main/.github/ISSUE_TEMPLATE/bug_report.yml
    * Features: https://github.com/pycontribs/jira/blob/main/.github/ISSUE_TEMPLATE/feature_request.yml

  * If possible, create a pull request with a (failing) test case demonstrating
    what's wrong. This makes the process for fixing bugs quicker & gets issues
    resolved sooner.


Issues
******
Here are the best ways to help with open issues:

* For issues without reproduction steps
    * Try to reproduce the issue, comment with the minimal amount of steps to
      reproduce the bug (a code snippet would be ideal).
    * If there is not a set of steps that can be made to reproduce the issue,
      at least make sure there are debug logs that capture the unexpected behavior.

* Submit pull requests for open issues.


Pull Requests
*************
There are some key points that are needed to be met before a pull request
can be merged:

* All tests must pass for all python versions. (Once the Test Framework is fixed)
    * For now, no new failures should occur

* All pull requests require tests that either test the new feature or test
  that the specific bug is fixed. Pull requests for minor things like
  adding a new region or fixing a typo do not need tests.
* Must follow PEP8 conventions.
* Within a major version changes must be backwards compatible.

The best way to help with pull requests is to comment on pull requests by
noting if any of these key points are missing, it will both help get feedback
sooner to the issuer of the pull request and make it easier to determine for
an individual with write permissions to the repository if a pull request
is ready to be merged.
