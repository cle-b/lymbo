.PHONY: setup format lint typing check test clean

setup:
	python -m pip install pip --upgrade
	pip install -e .
	pip install -r requirements-dev.txt


format:
	black lymbo tests examples

lint:
	black --check lymbo tests examples
	flake8 lymbo tests examples

typing:
	mypy

check: lint typing

test:
	python -m unittest tests/*.py

clean:
	rm -rf __pycache__
	rm -rf lymbo.egg-info
	rm -rf venv
	rm -rf build
	rm -rf dist
