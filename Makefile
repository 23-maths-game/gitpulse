.PHONY: help test lint fmt report demo clean build

PY ?= python
DEMO_DIR ?= /tmp/gitpulse-demo

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

test:  ## Run the test suite
	$(PY) -m pytest -q

lint:  ## Static checks
	$(PY) -m ruff check .

fmt:  ## Auto-fix lint issues
	$(PY) -m ruff check --fix .

report:  ## Analyse this repository
	$(PY) -m gitpulse . -o gitpulse-report.html --open

demo:  ## Rebuild the committed demo report
	$(PY) scripts/make_demo_repo.py $(DEMO_DIR)
	$(PY) -m gitpulse $(DEMO_DIR) -o docs/demo-report.html

build:  ## Build sdist + wheel
	$(PY) -m pip install -q build && $(PY) -m build

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info **/__pycache__
