#!/bin/bash
set -ex

VERSION=$(python -c "from jira.version import __version__ ; print __version__")
echo Preparing to release version $VERSION

echo === Chechink that all changes are commited and pushed ===
git pull -u

git diff
# Disallow unstaged changes in the working tree
    if ! git diff-files --check --exit-code --ignore-submodules -- >&2
    then
        echo >&2 "error: you have unstaged changes."
        #git diff-files --check --exit-code --ignore-submodules -- >&2
        exit 1
    fi

# Disallow uncommitted changes in the index
    if ! git diff-index --cached --exit-code -r --ignore-submodules HEAD -- >&2
    then
        echo >&2 "error: your index contains uncommitted changes."
        exit 1
    fi


echo "Please don't run this as a user. This generates a new release for PyPI. Press ^C to exit or Enter to continue."
read

git log --date=short --pretty=format:"%cd %s" > CHANGELOG
git add CHANGELOG
git tag -a $VERSION -m "Version $VERSION"
git tag -f -a RELEASE -m "Current RELEASE"

python setup.py register sdist bdist_wheel build_sphinx upload_docs upload --sign

git push --force origin --tags

echo "done."
