#!/usr/bin/env python

from setuptools import setup, find_packages

exec(open('jira/version.py').read())
setup(
    name='jira-python',
    version=__version__,
    packages=find_packages(),

    install_requires=['requests==0.12.1', 'ipython==0.12.1', 'argparse==1.2.1', 'python-magic==0.4.2',
                      'tlslite==0.4.1'],
#   can't get this working for the moment.
#    extras_require = {
#        'interactive-shell': ['ipython==0.12.1', 'argparse==1.2.1']
#    },
    entry_points = {
        'console_scripts':
            ['jirashell = tools.jirashell:main'],
    },

    url='http://bitbucket.org/bspeakmon_atlassian/jira-python',
    license='BSD',
    description='A library to ease use of the JIRA 5 REST APIs.',
    author='Ben Speakmon',
    author_email='bspeakmon@atlassian.com',
    provides=['jira'],
    keywords='jira',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
    ],
)