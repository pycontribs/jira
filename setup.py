#!/usr/bin/env python
# import codecs
import os
import sys
import warnings

from pip.req import parse_requirements
from setuptools import find_packages, setup

NAME = "jira"

base_path = os.path.dirname(__file__)
if base_path not in sys.path:
    sys.path.insert(0, base_path)


# this should help getting annoying warnings from inside distutils
warnings.simplefilter('ignore', UserWarning)


def _is_ordereddict_needed():
    """ Check if `ordereddict` package really needed """
    try:
        return False
    except ImportError:
        pass
    return True


def get_metadata(*path):
    fn = os.path.join(base_path, *path)
    scope = {'__file__': fn}

    # We do an exec here to prevent importing any requirements of this package.
    # Which are imported from anything imported in the __init__ of the package
    # This still supports dynamic versioning
    with open(fn) as fo:
        code = compile(fo.read(), fn, 'exec')
        exec(code, scope)

    if 'setup_metadata' in scope:
        return scope['setup_metadata']

    raise RuntimeError('Unable to find metadata.')


def read(fname):
    with open(os.path.join(base_path, fname)) as f:
        return f.read()


def get_requirements(*path):
    req_path = os.path.join(*path)
    reqs = parse_requirements(req_path, session=False)
    return [str(ir.req) for ir in reqs]

# class PyTest(TestCommand):
#     user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]
#
#     def initialize_options(self):
#         TestCommand.initialize_options(self)
#         self.pytest_args = []
#
#         logging.basicConfig(format='%(levelname)-10s %(message)s')
#         logging.getLogger("jira").setLevel(logging.INFO)
#
#         # if we have pytest-cache module we enable the test failures first mode
#         try:
#             import pytest_cache  # noqa
#             self.pytest_args.append("--ff")
#         except ImportError:
#             pass
#
#         if sys.stdout.isatty():
#             # when run manually we enable fail fast
#             self.pytest_args.append("--maxfail=1")
#         try:
#             import coveralls  # noqa
#             self.pytest_args.append("--cov=%s" % NAME)
#             self.pytest_args.extend(["--cov-report", "term"])
#             self.pytest_args.extend(["--cov-report", "xml"])
#
#         except ImportError:
#             pass
#
#     def finalize_options(self):
#         TestCommand.finalize_options(self)
#         self.test_args = []
#         self.test_suite = True
#
#     def run_tests(self):
#         # before running tests we need to run autopep8
#         try:
#             saved_argv = sys.argv
#             sys.argv = "-r --in-place jira/ tests/ examples/".split(" ")
#             runpy.run_module('autopep8')
#             sys.argv = saved_argv  # restore sys.argv
#         except subprocess.CalledProcessError:
#             logging.warning('autopep8 is not installed so '
#                             'it will not be run')
#         # import here, cause outside the eggs aren't loaded
#         import pytest
#         errno = pytest.main(self.pytest_args)
#         sys.exit(errno)


# class Release(Command):
#     user_options = []
#
#     def initialize_options(self):
#         # Command.initialize_options(self)
#         pass
#
#     def finalize_options(self):
#         # Command.finalize_options(self)
#         pass
#
#     def run(self):
#         import json
#         try:
#             from urllib.request import urlopen
#         except ImportError:
#             from urllib2 import urlopen
#         response = urlopen(
#             "https://pypi.python.org/pypi/%s/json" % NAME)
#         data = json.load(codecs.getreader("utf-8")(response))
#         released_version = data['info']['version']
#         if released_version == __version__:
#             raise RuntimeError(
#                 "This version was already released, remove it from PyPi if you want "
#                 "to release it again or increase the version number. https://pypi.python.org/pypi/%s/" % NAME)
#         elif released_version > __version__:
#             raise RuntimeError("Cannot release a version (%s) smaller than the PyPI current release (%s)." % (
#                 __version__, released_version))
#
#
# class PreRelease(Command):
#     user_options = []
#
#     def initialize_options(self):
#         # Command.initialize_options(self)
#         pass
#
#     def finalize_options(self):
#         # Command.finalize_options(self)
#         pass
#
#     def run(self):
#         import json
#         try:
#             from urllib.request import urlopen
#         except ImportError:
#             from urllib2 import urlopen
#         response = urlopen(
#             "https://pypi.python.org/pypi/%s/json" % NAME)
#         data = json.load(codecs.getreader("utf-8")(response))
#         released_version = data['info']['version']
#         if released_version >= __version__:
#             raise RuntimeError(
#                 "Current version of the package is equal or lower than the "
#                 "already published ones (PyPi). Increse version to be able to pass prerelease stage.")

if __name__ == '__main__':
    with open("README.rst") as f:
        readme = f.read()

    setup(
        name=NAME,
        # cmdclass={'release': Release, 'prerelease': PreRelease},
        packages=find_packages(exclude=['tests', 'tools']),
        include_package_data=True,

        install_requires=get_requirements(base_path, 'requirements.txt'),
        setup_requires=['pytest-runner'],
        tests_require=get_requirements(base_path, 'requirements-dev.txt'),
        extras_require={
            'all': [],
            'magic': ['filemagic>=1.6'],
            'shell': ['ipython>=0.13']},
        zip_safe=True,
        entry_points={
            'console_scripts':
            ['jirashell = jira.jirashell:main']},

        long_description=readme,
        provides=[NAME],
        bugtrack_url='https://github.com/pycontribs/jira/issues',
        home_page='https://github.com/pycontribs/jira',
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
            'Topic :: Software Development :: Libraries :: Python Modules'],
        # All metadata including version numbering is in here
        **get_metadata(base_path, NAME, 'package_meta.py')
    )
