# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from jira.utils.version import get_version


VERSION = (1, 0, 7, 'alpha', 0)

__version__ = get_version(VERSION)
__author__ = 'bspeakmon@atlassian.com'

from .config import get_jira  # noqa
from .client import JIRA, Priority, Comment, Worklog, Watchers, User, Role, Issue, Project  # noqa
from .exceptions import JIRAError  # noqa
