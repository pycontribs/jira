all: info clean lint test docs dist upload release
.PHONY: all docs upload info req dist

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

PREFIX := ""
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

hooks:
	@$(PREFIX)python -m flake8 --install-hook 2>/dev/null || true

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
	sh -c 'echo "deb https://sdkrepo.atlassian.com/debian/ stable contrib" >/etc/apt/sources.list.d/atlassian_development.list'
	apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys B07804338C015B73
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
	@pyenv install -s 2.7.13
	@pyenv install -s 3.4.5
	@pyenv install -s 3.5.2
	@pyenv install -s 3.6.0
	@pyenv local 2.7.13 3.4.5 3.5.2 3.6.0
	@echo "INFO:	=== Preparing to run for package:$(PACKAGE_NAME) platform:$(PLATFORM) py:$(PYTHON_VERSION) dir:$(DIR) ==="
	#if [ -f ${HOME}/testspace/testspace ]; then ${HOME}/testspace/testspace config url ${TESTSPACE_TOKEN}@pycontribs.testspace.com/jira/tests ; fi;

testspace:
	${HOME}/testspace/testspace publish build/results.xml

lint:
	@echo "INFO:	linting...."
	$(PREFIX)python -m flake8

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
# cannot put doc2dash into requirements.txt file because is using pinned requirements
#	@DOC2DASH_OPTS=$(shell [ -d "$HOME/Library/Application Support/doc2dash/DocSets" ] && echo '--add-to-global')
#	doc2dash --force --name jira docs/build/html --destination docs/build/docset --icon docs/_static/python-32.png --online-redirect-url https://jira.readthedocs.io/en/stable/ $(DOC2DASH_OPTS)
#	cd docs/build/docset && tar --exclude='.DS_Store' -czf ../html/docset/jira.tgz jira.docset
#	# TODO: publish the docs

tag:
	bumpversion --feature --no-input
	git push origin master
	git push --tags

release: req
ifeq ($(GIT_BRANCH),master)
	tag
else
	upload
	web

	@echo "INFO:	Skipping release on this branch."
endif

upload:
	rm -f dist/*
ifeq ($(GIT_BRANCH),develop)
	@echo "INFO:	Upload package to testpypi.python.org"
	$(PREFIX)python setup.py check --restructuredtext --strict
	$(PREFIX)python setup.py sdist bdist_wheel
	$(PREFIX)twine upload --repository-url https://test.pypi.org/legacy/ dist/*
endif
ifeq ($(GIT_BRANCH),master)
	@echo "INFO:	Upload package to pypi.python.org"
	$(PREFIX)python setup.py check --restructuredtext --strict
	$(PREFIX)python setup.py sdist bdist_wheel
	$(PREFIX)twine upload dist/*
endif
