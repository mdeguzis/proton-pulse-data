# proton-pulse-data — Makefile

UV_CACHE_DIR ?= /tmp/uv-cache

.PHONY: help setup test test-py

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  setup    Install Python dependencies with uv"
	@echo "  test     Run the test suite with uv"
	@echo "  test-py  Run the Python test suite with uv"

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --group dev

test: test-py

test-py:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --group dev python -m pytest tests/ -v
