all: clean install uninstall tox flake8 test pypi docs tag release
.PHONY: all docs

PACKAGE_NAME=$(shell python setup.py --name)

clean:
	find . -name "*.pyc" -delete

install:
	python setup.py install

uninstall:
	pip uninstall -y $(PACKAGE_NAME)

prepare:
	pip install -q -r requirements.txt
	pip install -q -r requirements-opt.txt
	pip install -q -r requirements-dev.txt

tox:
	pip install --user tox
	python -m tox

test: prepare flake8
	python setup.py test

flake8:
	python -m flake8
	python -m flake8 --install-hook 2>/dev/null || true

pypi:
	python setup.py check --restructuredtext --strict
	python setup.py sdist bdist_wheel upload

pypitest:
	python setup.py check --restructuredtext --strict
	python setup.py sdist bdist_wheel upload -r pypi-test

docs:
	pip install sphinx
	python setup.py build_sphinx
	#sphinx-build -b html docs/ docs/build/

tag:
	bumpversion minor
	git push origin master
	git push --tags

release:
	tag
	pypi
	web
