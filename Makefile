all: info clean lint test docs dist
.PHONY: all docs info req dist

PACKAGE_NAME := $(shell python setup.py --name)
PACKAGE_VERSION := $(shell python setup.py --version)
PYTHON_PATH := $(shell which python)
PLATFORM := $(shell uname -s | awk '{print tolower($$0)}')
ifeq ($(PLATFORM), darwin)
	DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
else
	DIR := $(shell dirname $(realpath $(MAKEFILE_LIST)))
endif
PYTHON_VERSION := $(shell python3 -c "import sys; print('py%s%s' % sys.version_info[0:2] + ('-conda' if 'conda' in sys.version or 'Continuum' in sys.version else ''))")
ifneq (,$(findstring conda, $(PYTHON_VERSION)))
	#CONDA := $(shell conda info --envs | grep '*' | awk '{print $$1}')
	CONDA := $(CONDA_DEFAULT_ENV)
endif

PREFIX :=
ifndef GIT_BRANCH
GIT_BRANCH=$(shell git branch | sed -n '/\* /s///p')
endif

info:
	@echo "INFO:	Building $(PACKAGE_NAME):$(PACKAGE_VERSION) on $(GIT_BRANCH) branch"
	@echo "INFO:	Python $(PYTHON_VERSION) from '$(PREFIX)' [$(CONDA)]"

clean:
	@find . -name "*.pyc" -delete
	@rm -rf .tox dist/* docs/build/*

package:
	python setup.py sdist bdist_wheel build_sphinx

req:
	@$(PREFIX)requires.io update-site -t ac3bbcca32ae03237a6aae2b02eb9411045489bb -r $(PACKAGE_NAME)

install: prepare
	$(PREFIX)pip install .

# https://developer.atlassian.com/docs/getting-started/set-up-the-atlassian-plugin-sdk-and-build-a-project/install-the-atlassian-sdk-on-a-linux-or-mac-system#InstalltheAtlassianSDKonaLinuxorMacsystem-Homebrew
install-sdk:
ifeq ($(PLATFORM), darwin)
	which atlas-run-standalone || brew tap atlassian/tap && brew install atlassian/tap/atlassian-plugin-sdk
else ifeq ($(PLATFORM), linux)
  ifneq ($(USER), root)
	@echo "Install of Atlassian SDK must be run as root (or with sudo)"
	exit 1
  endif
  ifneq ($(wildcard /etc/debian_version),)
	sh -c 'echo "deb https://packages.atlassian.com/atlassian-sdk-deb stable contrib" >/etc/apt/sources.list.d/atlassian_development.list'
	curl -fsSL https://packages.atlassian.com/api/gpg/key/public | apt-key add -
	apt-get install apt-transport-https
	apt-get update
	apt-get install atlassian-plugin-sdk
  else ifneq ($(wildcard /etc/redhat-release),)
	tmp_dir=$(mktemp -d)
	curl https://marketplace.atlassian.com/download/plugins/atlassian-plugin-sdk-rpm/version/42380 -o ${tmp_dir}/atlassian-plugin-sdk.noarch.rpm
	yum -y install ${tmp_dir}/atlassian-plugin-sdk.noarch.rpm
	rm -rf ${tmp_dir}
  else
	@echo "Error: Cannot determine package manager to use to install atlassian-sdk.  Please see:"
	@echo "https://developer.atlassian.com/docs/getting-started/set-up-the-atlassian-plugin-sdk-and-build-a-project/install-the-atlassian-sdk-on-a-linux-or-mac-system"
	exit 1
  endif
endif

uninstall:
	$(PREFIX)pip uninstall -y $(PACKAGE_NAME)

dist:
	$(PREFIX)python setup.py sdist bdist_wheel

prepare:
	@pyenv install -s 3.6.9
	@pyenv install -s 3.7.4
	@pyenv local 3.6.9 3.7.4
	@echo "INFO:	=== Preparing to run for package:$(PACKAGE_NAME) platform:$(PLATFORM) py:$(PYTHON_VERSION) dir:$(DIR) ==="
	#if [ -f ${HOME}/testspace/testspace ]; then ${HOME}/testspace/testspace config url ${TESTSPACE_TOKEN}@pycontribs.testspace.com/jira/tests ; fi;

testspace:
	${HOME}/testspace/testspace publish build/results.xml

lint:
	@echo "INFO:	linting...."
	$(PREFIX)tox -e lint

test: prepare lint
	@echo "INFO:	test"
	$(PREFIX)python setup.py build test build_sphinx sdist bdist_wheel check --restructuredtext --strict

test-all:
	@echo "INFO:	test-all (extended/matrix tests)"
	# tox should not run inside virtualenv because it does create and use multiple virtualenvs
	pip install -q tox tox-pyenv
	python -m tox

docs:
	@echo "INFO:	Building the docs"
	$(PREFIX)pip install sphinx sphinx_rtd_theme
	$(PREFIX)python setup.py build_sphinx
	@mkdir -p docs/build/docset
	@mkdir -p docs/build/html/docset

tag:
	bumpversion --feature --no-input
	git push origin master
	git push --tags
