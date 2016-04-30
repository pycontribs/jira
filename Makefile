all: clean install uninstall tox flake8 test pypi docs tag release
.PHONY: all

PACKAGE_NAME=$(shell python setup.py --name)

clean:
	find . -name "*.pyc" -delete

install:
	
	python setup.py install

uninstall:
	python -m pip uninstall -y $(PACKAGE_NAME)

prepare:
	python -m pip install -r requirements.txt
	python -m pip install -r requirements-opt.txt
	python -m pip install -r requirements-dev.txt

tox:
	python -m pip install --user tox
	python -m tox

test: prepare
	python setup.py test

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
