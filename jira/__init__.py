# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pkg_resources import get_distribution


__version__ = get_distribution('jira').version
__author__ = 'bspeakmon@atlassian.com'

from .config import get_jira  # noqa
from .client import JIRA, Priority, Comment, Worklog, Watchers, User, Role, Issue, Project  # noqa
from .exceptions import JIRAError  # noqa
