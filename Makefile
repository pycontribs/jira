all: clean install uninstall install_testrig tox flake8 test pypi docs tag release
.PHONY: all

PACKAGE_NAME=$(shell python setup.py --name)

clean:
	find . -name "*.pyc" -delete

install:
	python -m pip install -r requirements-dev.txt
	python setup.py install

uninstall:
	python -m pip uninstall -y $(PACKAGE_NAME)

install_testrig:
	python -m pip install --user nose mock

tox:
	python -m pip install --user tox
	python -m tox

test: install_testrig
	nosetests

flake8:
	python -m pip install flake8
	python -m flake8
	python -m flake8 --install-hook 2>/dev/null || true

pypi:
	python setup.py check --restructuredtext --strict
	python setup.py sdist bdist_wheel upload

pypitest:
	python setup.py check --restructuredtext --strict
	python setup.py sdist bdist_wheel upload -r pypi-test

docs:
	python -m pip install sphinx
	sphinx-build -b html docs/ docs/build/

tag:
	bumpversion minor
	git push origin master
	git push --tags

release:
	tag
	pypi
	web
