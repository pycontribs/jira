all: info clean flake8 test docs upload release
.PHONY: all docs upload info req

PACKAGE_NAME := $(shell python setup.py --name)
PACKAGE_VERSION := $(shell python setup.py --version)
PYTHON_PATH := $(shell which python)
PLATFORM := $(shell uname -s | awk '{print tolower($0)}')
DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYTHON_VERSION := $(shell python3 -c "import sys; print('py%s%s' % sys.version_info[0:2] + ('-conda' if 'conda' in sys.version or 'Continuum' in sys.version else ''))")
PYENV_HOME := $(DIR)/.tox/$(PYTHON_VERSION)-$(PLATFORM)/
ifneq (,$(findstring conda,$(PYTHON_VERSION)))
CONDA:=1
endif

ifndef GIT_BRANCH
GIT_BRANCH=$(shell git branch | sed -n '/\* /s///p')
endif

info:
	@echo "INFO:	Building $(PACKAGE_NAME):$(PACKAGE_VERSION) on $(GIT_BRANCH) branch"
	@echo "INFO:	Python $(PYTHON_VERSION) from $(PYENV_HOME) [$(CONDA)]"

clean:
	@find . -name "*.pyc" -delete
	@rm -rf .tox/*-$(PLATFORM) .tox/docs dist/* .tox/dist .tox/log docs/build/*

package:
	python setup.py sdist bdist_wheel build_sphinx

req:
	@$(PYENV_HOME)/bin/requires.io update-site -t ac3bbcca32ae03237a6aae2b02eb9411045489bb -r $(PACKAGE_NAME)

install: prepare
	$(PYENV_HOME)/bin/pip install .

install-sdk:
	# https://developer.atlassian.com/docs/getting-started/set-up-the-atlassian-plugin-sdk-and-build-a-project/install-the-atlassian-sdk-on-a-linux-or-mac-system#InstalltheAtlassianSDKonaLinuxorMacsystem-Homebrew
	which atlas-run-standalone || brew tap atlassian/tap && brew install atlassian/tap/atlassian-plugin-sdk

uninstall:
	$(PYENV_HOME)/bin/pip uninstall -y $(PACKAGE_NAME)

venv: $(PYENV_HOME)/bin/activate

# virtual environment depends on requriements files
$(PYENV_HOME)/bin/activate: requirements*.txt
	@echo "INFO:	(Re)creating virtual environment..."
ifdef CONDA
	test -e $(PYENV_HOME)/bin/activate || conda create -y --prefix $(PYENV_HOME) pip
else
	test -e $(PYENV_HOME)/bin/activate || virtualenv --python=$(PYTHON_PATH) --system-site-packages $(PYENV_HOME)
endif
	$(PYENV_HOME)/bin/pip install -q -r requirements.txt -r requirements-opt.txt -r requirements-dev.txt
	touch $(PYENV_HOME)/bin/activate

prepare: venv
	pyenv install -s 2.7.13
	pyenv install -s 3.4.5
	pyenv install -s 3.5.2
	pyenv install -s 3.6.0
	pyenv local 2.7.13 3.4.5 3.5.2 3.6.0
	@echo "INFO:	=== Prearing to run for package:$(PACKAGE_NAME) platform:$(PLATFORM) py:$(PYTHON_VERSION) dir:$(DIR) ==="
	if [ -f ${HOME}/testspace/testspace ]; then ${HOME}/testspace/testspace config url ${TESTSPACE_TOKEN}@pycontribs.testspace.com/jira/tests ; fi;

testspace:
	${HOME}/testspace/testspace publish build/results.xml

flake8: venv
	@echo "INFO:	flake8"
	$(PYENV_HOME)/bin/python -m flake8
	$(PYENV_HOME)/bin/python -m flake8 --install-hook 2>/dev/null || true

test: prepare flake8
	@echo "INFO:	test"
	$(PYENV_HOME)/bin/python setup.py build test build_sphinx sdist bdist_wheel check --restructuredtext --strict

test-cli:
	$(PYENV_HOME)/bin/ipython -c "import jira; j = jira.JIRA('https://pycontribs.atlassian.net'); j.server_info()" -i

test-all:
	@echo "INFO:	test-all (extended/matrix tests)"
	# tox should not run inside virtualenv because it does create and use multiple virtualenvs
	pip install -q tox tox-pyenv
	python -m tox --skip-missing-interpreters true


docs:
	@echo "INFO:	Building the docs"
	$(PYENV_HOME)/bin/pip install sphinx
	$(PYENV_HOME)/bin/python setup.py build_sphinx
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
ifeq ($(GIT_BRANCH),develop)
	@echo "INFO:	Upload package to testpypi.python.org"
	$(PYENV_HOME)/bin/python setup.py check --restructuredtext --strict
	$(PYENV_HOME)/bin/python setup.py sdist bdist_wheel upload -r https://testpypi.python.org/pypi
endif
ifeq ($(GIT_BRANCH),master)
	@echo "INFO:	Upload package to pypi.python.org"
	$(PYENV_HOME)/bin/python setup.py check --restructuredtext --strict
	$(PYENV_HOME)/bin/python setup.py sdist bdist_wheel upload
endif
