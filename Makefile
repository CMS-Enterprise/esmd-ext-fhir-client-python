# EsmdFHIRClient Makefile
# Common development tasks

.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build docs setup

# Default target
help:
	@echo "EsmdFHIRClient Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup         - Set up development environment"
	@echo "  install       - Install package in production mode"
	@echo "  install-dev   - Install package in development mode with dev dependencies"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-cov      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint          - Run linting (flake8)"
	@echo "  format        - Format code (black)"
	@echo "  type-check    - Run type checking (mypy)"
	@echo "  quality       - Run all quality checks"
	@echo ""
	@echo "Build Commands:"
	@echo "  clean         - Clean build artifacts"
	@echo "  build         - Build package"
	@echo "  build-all     - Build all modules with shared dependencies"
	@echo "  build-shared  - Build shared module only"
	@echo "  build-bundle  - Build bundle submission module"
	@echo "  build-practitioner - Build practitioner module"
	@echo "  build-document - Build document scheduler module"
	@echo "  build-notification - Build notification scheduler module"
	@echo "  docs          - Build documentation"
	@echo ""
	@echo "Utility Commands:"
	@echo "  config-check  - Validate configuration"
	@echo "  deps-check    - Check for dependency updates"

# Setup and Installation
setup: clean install-dev
	@echo "Development environment setup complete!"

install:
	pip install .

install-dev:
	pip install -e ".[dev,testing,docs]"
	pip install pre-commit
	pre-commit install

# Testing
test:
	pytest

test-unit:
	pytest -m "unit"

test-integration:
	pytest -m "integration" --runintegration

test-network:
	pytest -m "network" --runnetwork

test-slow:
	pytest -m "slow" --runslow

test-cov:
	pytest --cov-report=html --cov-report=term

test-cov-xml:
	pytest --cov-report=xml

# Code Quality
lint:
	flake8 esmd_shared bundlesubmissionclient documentrefscheduler notificationscheduler practitionerclient

format:
	black esmd_shared bundlesubmissionclient documentrefscheduler notificationscheduler practitionerclient tests

format-check:
	black --check esmd_shared bundlesubmissionclient documentrefscheduler notificationscheduler practitionerclient tests

type-check:
	mypy esmd_shared bundlesubmissionclient documentrefscheduler notificationscheduler practitionerclient

quality: format-check lint type-check
	@echo "All quality checks passed!"

# Build and Distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	python setup.py sdist bdist_wheel

# Module-specific builds (with shared module dependency)
build-shared:
	cd esmd_shared && python setup.py install --user

build-bundle: build-shared
	cd bundlesubmissionclient && python setup.py install --user

build-practitioner: build-shared
	cd practitionerclient && python setup.py install --user

build-document: build-shared
	cd documentrefscheduler && python setup.py install --user

build-notification: build-shared
	cd notificationscheduler && python setup.py install --user

build-modules: build-shared
	python build_modules.py

# Quick build all modules
build-all: clean build-modules

build-check:
	python -m twine check dist/*

upload-test:
	python -m twine upload --repository testpypi dist/*

upload:
	python -m twine upload dist/*

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000

docs-clean:
	cd docs && make clean

# Utility Commands
config-check:
	python -c "from esmd_shared import ConfigUtility; config = ConfigUtility(); print('Config valid:', config.validate_required_config())"

auth-check:
	python -c "from esmd_shared import EsmdAuthClient; auth = EsmdAuthClient(); token = auth.get_token(); print('Auth successful:', token is not None)"

deps-check:
	pip list --outdated

deps-update:
	pip-review --local --auto

# Development Helpers
install-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

run-hooks:
	pre-commit run --all-files

# Quick development workflow
dev-check: format lint type-check test-unit
	@echo "Quick development check complete!"

# Full CI workflow
ci: quality test test-cov build
	@echo "Full CI workflow complete!"

# Example commands for testing modules
test-auth:
	pytest tests/test_shared_auth.py -v

test-config:
	pytest tests/test_shared_config.py -v

test-bundle:
	pytest tests/test_bundle* -v

# Security checks (if bandit is installed)
security-check:
	bandit -r esmd_shared bundlesubmissionclient documentrefscheduler notificationscheduler practitionerclient

# Performance profiling (if needed)
profile:
	python -m cProfile -o profile.out -s cumulative examples/benchmark.py
	python -c "import pstats; pstats.Stats('profile.out').print_stats(20)"

# Environment information
env-info:
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Virtual environment: $$VIRTUAL_ENV"
	@echo "Working directory: $$(pwd)" 