# Makefile for common operations
.PHONY: help setup test test-unit test-integration test-system test-all clean coverage

# Default command
all: help

help:
	@echo "Available commands:"
	@echo "  make setup              - Set up the development environment"
	@echo "  make test              - Run all tests (simple)"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-system       - Run system tests only"
	@echo "  make test-all          - Run comprehensive test suite"
	@echo "  make coverage          - Generate test coverage report"
	@echo "  make run               - Start the API server"
	@echo "  make clean             - Clean up temporary files"

setup:
	@scripts/setup.sh

test:
	@scripts/run_tests.sh

test-unit:
	@scripts/run_tests.sh unit

test-integration:
	@scripts/run_tests.sh integration

test-system:
	@scripts/run_tests.sh system

test-all:
	@scripts/run_tests.sh all true

coverage:
	@echo "📊 Generating coverage report..."
	@source .venv/bin/activate && pytest --cov=app --cov-report=html --cov-report=term
	@echo "✅ Coverage report available at htmlcov/index.html"

run:
	@echo "Starting the API server..."
	@source .venv/bin/activate && uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache
	@rm -f .coverage
	@rm -rf htmlcov
	@echo "✅ Cleanup complete."
release:
	@if [ -z "$$TAG" ]; then echo "Usage: make release TAG=v0.1.0"; exit 1; fi
	git tag -a $$TAG -m "release $$TAG"
	git push origin $$TAG
