.PHONY: setup format lint typing check test clean

setup:
	python -m pip install pip --upgrade
	pip install -e .
	pip install -r requirements-dev.txt


format:
	black lymbo 

lint:
	black --check lymbo
	flake8 lymbo

typing:
	mypy

check: lint typing

test:
	pytest -v -m tests/

clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf lymbo.egg-info
	rm -rf venv
	rm -rf build
	rm -rf dist
