.PHONY: help install clean lint format test

help: # Prints help for targets with comments
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?# .*$$' | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: # Install dependencies for development
	pip install --upgrade pip
	pip install -e .
	pip install -r requirements/dev.txt

clean: # Remove cache and build files
	find . -iname "*__pycache__" | xargs rm -rf
	find . -iname "*.pyc" | xargs rm -rf
	rm -rf .pytest_cache
	rm -rf build
	rm -rf dist

lint: # Check linting by ruff
	ruff check .

format: # Format code by black and ruff
	black .
	ruff check --fix .

test: clean lint # Clean cache, check lint and run tests
	pytest -v --cov=src tests
