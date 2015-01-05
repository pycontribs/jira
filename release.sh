#!/bin/bash
set -ex

VERSION=$(python -c "from jira.version import __version__ ; print __version__")
echo Preparing to release version $VERSION


#source tox

#pip install --upgrade pep8 autopep8 docutils

echo === Testings ===
#if ! python setup.py test; then
#	echo "The test suite failed. Fix it!"
#	exit 1
#fi

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


# Clear old distutils stuff
rm -rf build dist MANIFEST &> /dev/null

# Build installers, etc. and upload to PyPI
# python setup.py register sdist bdist_wininst upload

#python setup.py register sdist build_sphinx upload upload_sphinx
python setup.py register sdist bdist_wheel upload

git tag -f -a $VERSION -m "Version $VERSION"
git tag -f -a RELEASE -m "Current RELEASE"

git push --force origin --tags

echo "done."
