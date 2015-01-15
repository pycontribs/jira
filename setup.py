#!/usr/bin/env python
import os
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
from setuptools import Command

NAME = "jira"
#exec(open('%s/version.py' % NAME).read())
from jira import __version__

import warnings
import logging


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

        FORMAT = '%(levelname)-10s %(message)s'
        logging.basicConfig(format=FORMAT)
        logging.getLogger().setLevel(logging.INFO)

        # if we have pytest-cache module we enable the test failures first mode
        try:
            import pytest_cache
            self.pytest_args.append("--ff")
        except ImportError:
            pass

        # try:
        #     import pytest_instafail
        #     self.pytest_args.append("--instafail")
        # except ImportError:
        #     pass
        self.pytest_args.append("-s")

        if sys.stdout.isatty():
            # when run manually we enable fail fast
            self.pytest_args.append("--maxfail=2")

        try:
            import coveralls
            self.pytest_args.append("--cov=%s" % NAME)
            self.pytest_args.extend(["--cov-report", "xml"])

        except ImportError:
            pass

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # before running tests we need to run autopep8
        r = os.system(
            "python -m autopep8 -r --in-place jira/ tests/ examples/")
        if r:
            raise Exception("autopep8 failed")

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
        import urllib2
        response = urllib2.urlopen(
            "http://pypi.python.org/pypi/%s/json" % NAME)
        data = json.load(response)
        released_version = data['info']['version']
        if released_version == __version__:
            raise RuntimeError(
                "This version was already released, remove it from PyPi if you want to release it again or increase the version number. http://pypi.python.org/pypi/%s/" % NAME)
        elif released_version > __version__:
            raise RuntimeError("Cannot release a version (%s) smaller than the PyPI current release (%s)." % (
                __version__, released_version))

        sys.exit()

setup(
    name=NAME,
    version=__version__,
    cmdclass={'test': PyTest, 'release': Release},
    packages=find_packages(exclude=['tests', 'tools']),
    include_package_data=True,
    # test_suite='nose.collector',

    install_requires=['requests>=1.2.3',
                      'requests_oauthlib>=0.3.3',
                      'tlslite>=0.4.4',
                      'six>=1.5.2',
                      'requests_toolbelt'],
    setup_requires=[],
    tests_require=['pytest', 'tlslite>=0.4.4', 'requests>=2.0',
                   'setuptools', 'pep8', 'autopep8', 'sphinx', 'six>=1.9.0'],
    extras_require={
        'magic': ['filemagic>=1.6'],
        'shell': ['ipython>=0.13'],
    },
    entry_points={
        'console_scripts':
        ['jirashell = jira.jirashell:main'],
    },

    url='https://github.com/pycontribs/jira',
    license='BSD',
    description='Python library for interacting with JIRA via REST APIs.',
    long_description=open("README.rst").read(),
    author='Ben Speakmon',
    author_email='ben.speakmon@gmail.com',
    provides=[NAME],
    keywords='jira atlassian rest api',
    bugtrack_url='https://github.com/pycontribs/jira/issues',
    home_page='https://github.com/pycontribs/jira',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
