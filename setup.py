#!/usr/bin/env python
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

exec(open('jira/version.py').read())
setup(
    name='jira',  # was jira-python
    version=__version__,
    cmdclass = {'test': PyTest},
    packages=find_packages(exclude=['tests', 'tools']),
    include_package_data=True,
    # test_suite='nose.collector',

    install_requires=['requests>=1.2.3',
                      'requests_oauthlib>=0.3.3',
                      'tlslite>=0.4.4',
                      'six>=1.5.2'],
    setup_requires=[],
    tests_require=['pytest', 'tlslite>=0.4.4', 'requests>=2.0', 'setuptools', 'pep8', 'autopep8', 'sphinx', 'six>=1.9.0'],
    extras_require={
        'magic': ['filemagic>=1.6'],
        'shell': ['ipython>=0.13'],
    },
    entry_points={
        'console_scripts':
        ['jirashell = jira.jirashell:main'],
    },

    url='http://bitbucket.org/bspeakmon/jira-python',
    license='BSD',
    description='A library to ease use of the JIRA 5 REST APIs.',
    long_description=open("README.rst").read(),
    author='Ben Speakmon',
    author_email='ben.speakmon@gmail.com',
    provides=['jira'],
    keywords='jira atlassian rest api',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
