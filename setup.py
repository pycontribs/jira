#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='jira-rest-client',
    version='0.5.0',
    packages=find_packages(),
    scripts=['tools/jirashell'],

    install_requires=['requests==0.11.2', 'simplejson==2.5.0', 'argparse==1.2.1',],
    extras_require = {
        'jirashell': ['ipython==0.12.1']
    },

    url='http://bitbucket.org/bspeakmon_atlassian/jira5-python',
    license='BSD',
    description='A library to ease use of the JIRA 5 REST APIs.',
    author='Ben Speakmon',
    author_email='bspeakmon@atlassian.com',
    provides=['jira'],
    keywords='jira',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
)