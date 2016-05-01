# -*- coding: utf-8 -*-
# Store the version here so:
# 1) we don't load dependencies by storing it in __init__.py
# 2) we can import it in setup.py for the same reason
# 3) we can import it into the jira module
import datetime
import os
import subprocess

VERSION = (1, 0, 6, 'final', 0)


def get_version(version, filename=None):
    assert len(version) == 5
    assert version[3] in ('a', 'beta', 'rc', 'final')
    main = '.'.join(map(str, version[:3]))
    sub = ''
    # everything build based on develop branch is a .dev build
    # develop is the integration branch for git flow adopters
    if (version[3] == 'a' and version[4] == 0) or get_git_branch() == 'develop':
        git_changeset = get_git_changeset(filename)
        if git_changeset:
            sub = '.dev%s' % git_changeset
    if version[3] != 'final' and not sub:
        sub = '%s%s' % tuple(version[3:])
    return main + sub


def sh(command, cwd=None):
    return subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            cwd=cwd,
                            universal_newlines=True).communicate()[0]


def get_git_changeset(filename=None):
    """Returns a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.
    """
    dirname = os.path.dirname(filename or __file__)
    git_show = sh('git show --pretty=format:%ct --quiet HEAD',
                  cwd=dirname)
    timestamp = git_show.partition('\n')[0]
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        return None
    return timestamp.strftime('%Y%m%d%H%M%S')


def get_git_branch():
    # Jenkins may not do a full checkout so we use the branch reported via env variables.
    if 'BRANCH_NAME' in os.environ:
        branch = os.environ['BRANCH_NAME']
    elif 'GIT_BRANCH' in os.environ:
        branch = '/'.join(os.environ['GIT_BRANCH'].split('/')[1:])
    else:
        branch = sh("git branch | sed -n '/\* /s///p'").rstrip()
    return branch


FORMAT = '%n'.join(['%H', '%aN', '%ae', '%cN', '%ce', '%s'])


def gitrepo(root=None):
    if not root:
        cwd = root = os.getcwd()
    else:
        cwd = os.getcwd()
        if cwd != root:
            os.chdir(root)
    gitlog = sh('git --no-pager log -1 --pretty="format:%s"' % FORMAT,
                cwd=root).split('\n', 5)
    branch = sh('git rev-parse --abbrev-ref HEAD', cwd=root).strip()
    remotes = [x.split() for x in
               filter(lambda x: x.endswith('(fetch)'),
                      sh('git remote -v', cwd=root).strip().splitlines())]
    if cwd != root:
        os.chdir(cwd)
    return {
        "head": {
            "id": gitlog[0],
            "author_name": gitlog[1],
            "author_email": gitlog[2],
            "committer_name": gitlog[3],
            "committer_email": gitlog[4],
            "message": gitlog[5].strip(),
        },
        "branch": branch,
        "remotes": [{'name': remote[0], 'url': remote[1]}
                    for remote in remotes]
    }

__version__ = get_version(VERSION)
