vpath %.whl ./dist
vpath %.tar.gz ./dist

build: %.whl %.tar.gz

%.whl %.tar.gz: pyproject.toml
	python -m build

pypi_upload: build
	python -m twine upload dist/*

test_pypi_upload: build
	python -m twine upload --repository testpypi dist/*

clean:
	rm dist/*.whl
	rm dist/*.tar.gz