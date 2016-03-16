#!/bin/bash
set -e

vercomp () {
    if [[ $1 == $2 ]]
    then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done
    return 0
}

testvercomp () {
    vercomp $1 $2
    case $? in
        0) op='=';;
        1) op='>';;
        2) op='<';;
    esac
    if [[ $op != $3 ]]
    then
        echo "FAIL: Expected '$3', Actual '$op', Arg1 '$1', Arg2 '$2'"
    else
        echo "Pass: '$1 $op $2'"
    fi
}

TAG=$(git describe $(git rev-list --tags --max-count=1))
VERSION=$(python -c "from jira.version import __version__ ; print __version__")
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

git log --date=short --pretty=format:"%cd %s" > CHANGELOG

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
sed -i.bak "s/${VERSION}/${NEW_VERSION}/" jira/version.py

git commit -m "Auto-increasing the version number after a release."

# disables because this is done only by Travis CI from now, which calls this script after that.
#python setup.py register sdist bdist_wheel build_sphinx upload_docs upload --sign

git push --force origin --tags

echo "INFO: done."
