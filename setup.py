#!/usr/bin/env python

from setuptools import setup, find_packages

exec(open('jira/version.py').read())
setup(
    name='jira', # was jira-python
    version=__version__,
    packages=find_packages(exclude=['tests','tools']),
    include_package_data=True,
    #test_suite='nose.collector',

    install_requires=['requests>=1.2.3',
                      'requests_oauthlib>=0.3.3',
                      'tlslite>=0.4.4'],
    setup_requires=['sphinx', 'requests_oauthlib'],
    tests_require=['tlslite>=0.4.4','xmlrunner>=1.7.3', 'requests>=1.2.3'],
    extras_require={
        'magic': ['filemagic>=1.6'],
        'shell': ['ipython>=0.13'],
    },
    entry_points={
        'console_scripts':
        ['jirashell = tools.jirashell:main'],
    },

    url='http://bitbucket.org/bspeakmon/jira-python',
    license='BSD',
    description='A library to ease use of the JIRA 5 REST APIs.',
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
