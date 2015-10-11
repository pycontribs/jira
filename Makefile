.PHONY: clean install uninstall install_testrig tox test travis flake8 pypi docs web tag release
clean:
	find . -name "*.pyc" -delete

install:
	python setup.py install

uninstall:
	pip uninstall blackhole

install_testrig:
	pip install --user nose mock

tox:
	pip install --user tox detox
	detox

test: install_testrig
	nosetests

flake8:
	pip install flake8
	flake8 blackhole --ignore="F403"

pypi:
	python setup.py check --restructuredtext --strict
	#python setup.py sdist upload
	#python2.6 setup.py bdist_wheel upload
	python2.7 setup.py bdist_wheel upload
	#python3.4 setup.py bdist_wheel upload

pypitest:
	python setup.py check --restructuredtext --strict
	python2.7 setup.py bdist_wheel upload

docs:
	pip install sphinx
	sphinx-build -b html docs/ docs/build/

web: docs
	rsync -e "ssh -p 2222" -P -rvz --delete docs/build/ kura@blackhole.io:/var/www/blackhole.io/

tag:
	bumpversion minor
	git push origin master
	git push --tags

release:
	tag
	pypi
	web
