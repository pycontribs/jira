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

To test code run::

    make test-all

This will run the code in a virtual environment, and will test across the
versions of python which are installed. It will also install tox if it is
not already installed.

Alternatively if you do not have make you can always run::

    pip install tox
    tox

Issues and Feature Requests
***************************

* Check to see if there's an existing issue/pull request for the
  bug/feature. All issues are at https://github.com/pycontribs/jira/issues
  and pull requests are at https://github.com/pycontribs/jira/pulls.
* If there isn't an existing issue there, please file an issue. The ideal
  report includes:

  * A description of the problem/suggestion.
  * How to recreate the bug.
  * If relevant, including the versions of your:

    * Python interpreter (3.6, etc)
    * jira-python
    * Operating System and Version (Windows 7, OS X 10.10, Ubuntu 14.04, etc.)
    * IPython if using jirashell
    * Optionally of the other dependencies involved

  * If possible, create a pull request with a (failing) test case demonstrating
    what's wrong. This makes the process for fixing bugs quicker & gets issues
    resolved sooner.
  * Here is an template
    ::

        Description: <SUMMARIZE ISSUE>

        Python Interpreter: <VERSION>
        jira-python: <VERSION>
        OS: <OPERATING SYSTEM>
        IPython (Optional): <VERSION>
        Other Dependencies:

        Steps To Reproduce:
            1. <STEP>
            2. <STEP>
            3. <STEP>
            ...

        Stack Trace:
            <TRACE>


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
