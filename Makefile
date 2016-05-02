all: clean install uninstall tox flake8 test pypi docs tag release
.PHONY: all docs

PACKAGE_NAME=$(shell python setup.py --name)
PYTHON_VERSION=$(shell python -c "import sys; print('py%s%s' % sys.version_info[0:2])")
PYTHON_PATH=$(shell which python)
PLATFORM=$(shell uname -s | awk '{print tolower($0)}')
DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYENV_HOME := $(DIR)/.tox/$(PYTHON_VERSION)-$(PLATFORM)/

clean:
	find . -name "*.pyc" -delete

install:
	$(PYENV_HOME)/bin/python setup.py install

uninstall:
	$(PYENV_HOME)/bin/pip uninstall -y $(PACKAGE_NAME)

venv: $(PYENV_HOME)/bin/activate

# virtual environment depends on requriements files
$(PYENV_HOME)/bin/activate: requirements*.txt
	@echo "INFO:	(Re)creating virtual environment..."
	test -d $(PYENV_HOME)/bin/activate || virtualenv --python=$(PYTHON_PATH) --system-site-packages $(PYENV_HOME)
	$(PYENV_HOME)/bin/pip install -q -r requirements.txt
	$(PYENV_HOME)/bin/pip install -q -r requirements-opt.txt
	$(PYENV_HOME)/bin/pip install -q -r requirements-dev.txt
	touch $(PYENV_HOME)/bin/activate

prepare: venv
	@echo "INFO:	=== Prearing to run for package:$(PACKAGE_NAME) platform:$(PLATFORM) py:$(PYTHON_VERSION) dir:$(DIR) ==="

flake8:
	$(PYENV_HOME)/bin/python -m flake8
	$(PYENV_HOME)/bin/python -m flake8 --install-hook 2>/dev/null || true

test: prepare flake8
	$(PYENV_HOME)/bin/python setup.py test

test-all:
	# tox should not run inside virtualenv because it does create and use multiple virtualenvs
	pip install -q tox tox-pyenv
	python -m tox

pypi:
	$(PYENV_HOME)/bin/python setup.py check --restructuredtext --strict
	$(PYENV_HOME)/bin/python setup.py sdist bdist_wheel upload

pypitest:
	$(PYENV_HOME)/bin/python setup.py check --restructuredtext --strict
	$(PYENV_HOME)/bin/python setup.py sdist bdist_wheel upload -r pypi-test

docs:
	$(PYENV_HOME)/bin/pip install sphinx
	$(PYENV_HOME)/bin/python setup.py build_sphinx
	#sphinx-build -b html docs/ docs/build/

tag:
	bumpversion minor
	git push origin master
	git push --tags

release:
	tag
	pypi
	web
