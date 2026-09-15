.PHONY: install lint fmt type test check demo all

install:
	pip install -e ".[dev]"

lint:
	ruff check .

fmt:
	ruff format .

type:
	mypy

test:
	pytest -q

# Everything CI runs.
check: lint type test
	ruff format --check .

demo:
	orchbench demo

all: install check demo
