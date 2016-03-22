
MANAGE=python manage.py
PROJECT_NAME=project
FLAKE8_OPTS=--exclude=.git,migrations --max-complexity=10
SETTINGS=--settings=$(PROJECT_NAME).settings.test

.PHONY : clean rmenv all test coverage ensure_virtualenv

all: coverage

rmenv: clean
	rm -fr bin lib local include build initenv share man tmp

initenv:
	virtualenv .
	virtualenv . --relocatable
	virtualenv . --system-site-packages
	mkdir tmp
	echo '# Environment initialization placeholder. Do not delete. Use "make rmenv" to remove environment.' > $@

ensure_virtualenv:
	@if [ -z $$VIRTUAL_ENV ]; then \
		echo "Please run me inside virtualenv.";  \
		exit 1; \
	fi

test:  ensure_virtualenv
	$(MANAGE) test --where=. $(SETTINGS) --with-xunit

coverage:  ensure_virtualenv
	$(MANAGE) test --where=. $(SETTINGS) \
		--with-xcoverage --with-xunit --cover-html  --cover-erase
lint:  ensure_virtualenv
	flake8 $(FLAKE8_OPTS) .


clean:
	find . -name '*.pyc' -exec rm '{}' ';'


reqs/dev: ensure_virtualenv
	pip install -r requirements/dev.txt  --download-cache=tmp/cache --src=tmp/src

reqs/test: ensure_virtualenv
	pip install -r requirements/test.txt --download-cache=tmp/cache --src=tmp/src

reqs/prod: ensure_virtualenv
	pip install -r requirements/prod.txt --download-cache=tmp/cache --src=tmp/src

dev-setup: ensure_virtualenv reqs/dev
	if [ ! -f $(PROJECT_NAME)/settings/local.py ]; then \
		echo 'from .dev import *' > $(PROJECT_NAME)/settings/local.py; \
	fi
	$(MANAGE) syncdb --all
	$(MANAGE) migrate --fake

test-setup: ensure_virtualenv reqs/test

dev-update: ensure_virtualenv reqs/dev
	$(MAKE) update

update: ensure_virtualenv
	$(MAKE) clean
	$(MANAGE) syncdb
	$(MANAGE) migrate
	$(MANAGE) collectstatic --noinput


migrate-init/%: ensure_virtualenv
	$(MANAGE) schemamigration $* --initial
	$(MANAGE) migrate $* --fake --delete-ghost-migrations

migrate-update/%: ensure_virtualenv
	$(MANAGE) schemamigration $*  --auto
	$(MANAGE) migrate $*
