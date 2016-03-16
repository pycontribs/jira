#!/bin/bash
set -e

VERSION=$(python -c "from jira.version import __version__ ; print __version__")
echo Preparing to release version $VERSION

echo === Checking that all changes are commited and pushed ===
git pull

#git diff
# Disallow unstaged changes in the working tree
    if ! git diff-files --check --exit-code --ignore-submodules -- >&2
    then
        echo >&2 "error: you have unstaged changes."
        exit 1
    fi

# Disallow uncommitted changes in the index
    if ! git diff-index --cached --exit-code -r --ignore-submodules HEAD -- >&2
    then
        echo >&2 "error: your index contains uncommitted changes."
        exit 1
    fi

git log --date=short --pretty=format:"%cd %s" > CHANGELOG
git diff

if [ -v PS1 ] ; then
  echo "Automatic deployment"
else
  echo "Please don't run this as a user. This generates a new release for PyPI. Press ^C to exit or Enter to continue."
  read
fi

git add CHANGELOG
git commit -a "Auto-generating release notes."

git tag -a $VERSION -m "Version $VERSION"
git tag -f -a RELEASE -m "Current RELEASE"

NEW_VERSION="${VERSION%.*}.$((${VERSION##*.}+1))"
set -ex
sed -i ~ "s/${VERSION}/${NEW_VERSION}/" jira/version.py

git commit -a "Auto-increasing the version number after a release."

# disables because this is done only by Travis CI from now, which calls this script after that.
#python setup.py register sdist bdist_wheel build_sphinx upload_docs upload --sign

git push --force origin --tags

echo "done."
