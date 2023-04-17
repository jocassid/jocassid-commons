vpath %.whl ./dist
vpath %.tar.gz ./dist
vpath %.py ./src/jocassid_commons ./tests

build: %.whl %.tar.gz

%.whl %.tar.gz: pyproject.toml clean
	python -m build

pypi_upload: build
	python -m twine upload dist/*

test_pypi_upload: build
	python -m twine upload --repository testpypi dist/*

test:
	pytest

clean:
	rm -f dist/*.whl
	rm -f dist/*.tar.gz