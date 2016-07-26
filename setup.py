#!/usr/bin/env python
import logging
import os
import runpy
import sys
import subprocess
import warnings
import codecs

from setuptools import setup, find_packages, Command
from setuptools.command.test import test as TestCommand

NAME = "jira"

here = os.path.dirname(__file__)
if here not in sys.path:
    sys.path.insert(0, here)

__version__ = '1.0.7'

# this should help getting annoying warnings from inside distutils
warnings.simplefilter('ignore', UserWarning)


def _is_ordereddict_needed():
    """ Check if `ordereddict` package really needed """
    try:
        return False
    except ImportError:
        pass
    return True


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

        logging.basicConfig(format='%(levelname)-10s %(message)s')
        logging.getLogger("jira").setLevel(logging.INFO)

        # if we have pytest-cache module we enable the test failures first mode
        try:
            import pytest_cache  # noqa
            self.pytest_args.append("--ff")
        except ImportError:
            pass

        if sys.stdout.isatty():
            # when run manually we enable fail fast
            self.pytest_args.append("--maxfail=1")
        try:
            import coveralls  # noqa
            self.pytest_args.append("--cov=%s" % NAME)
            self.pytest_args.extend(["--cov-report", "term"])
            self.pytest_args.extend(["--cov-report", "xml"])

        except ImportError:
            pass

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # before running tests we need to run autopep8
        try:
            saved_argv = sys.argv
            sys.argv = "-r --in-place tests/".split(" ")
            runpy.run_module('autopep8')
            sys.argv = saved_argv  # restore sys.argv
        except subprocess.CalledProcessError:
            logging.warning('autopep8 is not installed so '
                            'it will not be run')
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


class Release(Command):
    user_options = []

    def initialize_options(self):
        # Command.initialize_options(self)
        pass

    def finalize_options(self):
        # Command.finalize_options(self)
        pass

    def run(self):
        import json
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen
        response = urlopen(
            "https://pypi.python.org/pypi/%s/json" % NAME)
        data = json.load(codecs.getreader("utf-8")(response))
        released_version = data['info']['version']
        if released_version == __version__:
            raise RuntimeError(
                "This version was already released, remove it from PyPi if you want "
                "to release it again or increase the version number. https://pypi.python.org/pypi/%s/" % NAME)
        elif released_version > __version__:
            raise RuntimeError("Cannot release a version (%s) smaller than the PyPI current release (%s)." % (
                __version__, released_version))


class PreRelease(Command):
    user_options = []

    def initialize_options(self):
        # Command.initialize_options(self)
        pass

    def finalize_options(self):
        # Command.finalize_options(self)
        pass

    def run(self):
        import json
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen
        response = urlopen(
            "https://pypi.python.org/pypi/%s/json" % NAME)
        data = json.load(codecs.getreader("utf-8")(response))
        released_version = data['info']['version']
        if released_version >= __version__:
            raise RuntimeError(
                "Current version of the package is equal or lower than the already published ones (PyPi). Increse version to be able to pass prerelease stage.")


setup(
    name=NAME,
    version=__version__,
    cmdclass={'test': PyTest, 'release': Release, 'prerelease': PreRelease},
    packages=find_packages(exclude=['tests', 'tools']),
    include_package_data=True,

    install_requires=['requests>=2.6.0',
                      'requests_oauthlib>=0.3.3',
                      'tlslite>=0.4.4',
                      'six>=1.9.0',
                      'requests_toolbelt'] + (['ordereddict'] if _is_ordereddict_needed() else []),
    tests_require=['pytest', 'tlslite>=0.4.4', 'requests>=2.6.0',
                   'setuptools', 'pep8', 'autopep8', 'sphinx', 'sphinx_rtd_theme', 'six>=1.9.0',
                   'pytest-cov', 'pytest-pep8', 'pytest-instafail',
                   'pytest-xdist',
                   ],
    extras_require={
        'all': [],
        'magic': ['filemagic>=1.6'],
        'shell': ['ipython>=0.13']},
    entry_points={
        'console_scripts':
        ['jirashell = jira.jirashell:main']},

    license='BSD',
    description='Python library for interacting with JIRA via REST APIs.',
    long_description=open("README.rst").read(),
    maintainer='Sorin Sbarnea',
    maintainer_email='sorin.sbarnea@gmail.com',
    author='Ben Speakmon',
    author_email='ben.speakmon@gmail.com',
    provides=[NAME],
    url='https://github.com/pycontribs/jira',
    bugtrack_url='https://github.com/pycontribs/jira/issues',
    home_page='https://github.com/pycontribs/jira',
    download_url='https://github.com/pycontribs/jira/archive/%s.tar.gz' % __version__,
    keywords='jira atlassian rest api',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules'])
