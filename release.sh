#!/bin/bash
set -e

TAG=$(git describe $(git rev-list --tags --max-count=1))
VERSION=$(python setup.py --version)
echo "INFO: Preparing to release version ${VERSION} based on git tag ${TAG}"

exit 1

if testvercomp $TAG $VERSION '<'; then
    echo "."
else
    echo >&2 "ERROR: Current version and git tag do not match, cannot make release."
    exit 1
fi

echo "INFO: Checking that all changes are commited and pushed"
git pull

#git diff
# Disallow unstaged changes in the working tree
    if ! git diff-files --check --exit-code --ignore-submodules -- >&2
    then
        echo >&2 "ERROR:    You have unstaged changes."
        #exit 1
    fi

# Disallow uncommitted changes in the index
    if ! git diff-index --cached --exit-code -r --ignore-submodules HEAD -- >&2
    then
        echo >&2 "ERROR:    Your index contains uncommitted changes."
        #exit 1
    fi

# Use the gitchangelog tool to re-generate automated changelog
gitchangelog > CHANGELOG

if [ -z ${CI+x} ]; then
    echo "WARN: Please don't run this as a user. This generates a new release for PyPI. Press ^C to exit or Enter to continue."
else
    echo "INFO: Automatic deployment"
fi

git add CHANGELOG
git commit -m  "Auto-generating release notes."

git tag -fa ${VERSION} -m "Version ${VERSION}"
git tag -fa -a RELEASE -m "Current RELEASE"

NEW_VERSION="${VERSION%.*}.$((${VERSION##*.}+1))"
set -ex
sed -i.bak "s/${VERSION}/${NEW_VERSION}/" setup.py

git commit -m "Auto-increasing the version number after a release."

# disables because this is done only by Travis CI from now, which calls this script after that.
#python setup.py register sdist bdist_wheel build_sphinx upload --sign

git push --force origin --tags

echo "INFO: done."
