
PYTHON=python3.10
VENV=.venv

help:
	@echo
	@echo "PYTHON = $(PYTHON)"
	@echo "VENV   = $(VENV)"
	@echo
	@grep ':.*##' $(MAKEFILE_LIST) |\
		egrep -v 'grep|sed' |\
		sed -e 's/^\(.*\):.*\(##.*\)/\1\t\2/'
	@echo

checkpoint:  ## git add -u ; git commit -m "checkpoint"
	@ [ -d .tox/fmt ] && tox -e fmt || :
	@MESSAGE_="$(MESSAGE)" ; MESSAGE=$${MESSAGE:-checkpoint} ; \
	set -x ; git add -u ; git commit -m "$${MESSAGE}"

clean:  ## Remove .tox, htmlcov, etc...
	@echo "clean .coverage .tox htmlcov .mypy_cache .pytest_cache, tests//*.egg-info, tests//__pycache__"
	@ set +x ; \
		rm -rf .coverage .tox htmlcov .mypy_cache .pytest_cache \
			$$(find tests -name '*.egg-info') \
			$$(find tests -name __pycache__)

dev: $(VENV) $(VENV)/bin/tox  ## Setup virtual env for dev

fmt: $(VENV)/bin/tox  ## Format the code
	$(VENV)/bin/tox -e fmt

nuke: clean ## Remove everything
	@echo "nuke $(VENV), *.egg-info, __pycache__"
	@set +x ; \
		rm -rf $(VENV) \
			$$(find . -name '*.egg-info') \
			$$(find . -name __pycache__)

test: $(VENV)/bin/tox  ## Test everything
	$(VENV)/bin/tox --parallel

$(VENV)/bin/tox:
	$(VENV)/bin/pip install -e '.[dev]'

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e '.[all]'
