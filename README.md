FCS SRU Server
==============

<!-- START: BADGES -->
[![](https://img.shields.io/badge/%20code%20style-black-000000)](https://github.com/psf/black)
[![](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/)
[![](https://img.shields.io/badge/linting-flake8-yellowgreen)](https://github.com/PyCQA/flake8)  
[![](https://img.shields.io/badge/%20doc%20style-sphinx-0a507a.svg)](https://www.sphinx-doc.org/en/master/usage/index.html)
[![](https://img.shields.io/badge/%20doc%20style-google-3666d6.svg)](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings)  
[![fcs-sru-server @ PyPI](https://img.shields.io/pypi/v/fcs-sru-server)](https://pypi.python.org/pypi/fcs-sru-server)
[![](https://img.shields.io/github/last-commit/Querela/fcs-sru-server-python)](https://github.com/Querela/fcs-sru-server-python/commits/main)
[![Documentation Status](https://readthedocs.org/projects/fcs-sru-server-python/badge/?version=latest)](https://fcs-sru-server-python.readthedocs.io/en/latest/?badge=latest)
<!-- END: BADGES -->

- Based on [Java](https://github.com/clarin-eric/fcs-sru-server/) implementation  
  _git commit: `0091fca0a4add134c478beed422dd1399a5364e3`_
- Differences:
   - a bit more pythonic (naming, interfaces, enums etc.)
   - no auth stuff yet
   - WIP output buffering, server framework might not allow this,
     so no streaming and everything is in memory until sent
   - server framework choice (wsgi, asgi), for now [`werkzeug`](https://werkzeug.palletsprojects.com)
   - TODO: refactoring to allow async variants for streaming responses (large resources),
     e.g. with [`starlette`](https://www.starlette.io/)

## Summary

This package implements the server-side part of the SRU/CQL protocol (SRU/S)
and conforms to SRU version 1.1 and 1.2. SRU version 2.0 is mostly implemented
but might be missing some more obscure features.
The library will handle most of the protocol related tasks for you and you'll
only need to implement a few classes to connect you search engine. However, the
library will not save you from doing your SRU/CQL homework (i.e. you'll need to
have at least some understanding of the protocol and adhere to the protocol
semantics). Furthermore, you need to have at least some basic understanding of
Python web application development (wsgi in particular) to use this library.

More Information about SRU/CQL:
  http://www.loc.gov/standards/sru/

The implementation is designed to make very minimal assumptions about the
environment it's deployed in. For interfacing with your search engine, you
need to implement the `SRUSearchEngine` interface. At minimum, you'll need
to implement at least the `search()` method. Please check the Python API
documentation for further details about this interface.
The `SRUServer` implements the SRU protocol and uses your supplied search engine
implementation to talk to your search engine. The SRUServer is configured
using a `SRUServerConfig` instance. The `SRUServerConfig` reads an XML document,
which contains the (static) server configuration. It must conform to the
`sru-server-config.xsd` schema in the [`src/clarin/sru/xml/`](src/clarin/sru/xml/)
directory.


## Installation

```bash
# from github/source
python3 -m pip install 'fcs-sru-server @ git+https://github.com/Querela/fcs-sru-server-python.git'

# (locally) built package
python3 -m pip install dist/fcs_sru_server-<version>-py2.py3-none-any.whl
# or
python3 -m pip install dist/fcs-sru-server-<version>.tar.gz

# for local development
python3 -m pip install -e .
```

In `setup.cfg`:
```ini
[options]
install_requires =
    fcs-sru-server @ git+https://github.com/Querela/fcs-sru-server-python.git
```


## Build source/binary distribution

```bash
python3 -m pip install build
python3 -m build
```


## Development

* Uses `pytest` (with coverage, clarity and randomly plugins).

```bash
python3 -m pip install -e .[test]

pytest
```

Run style checks:
```bash
# general style checks
python3 -m pip install -e .[style]

black --check .
flake8 . --show-source --statistics
isort --check --diff .
mypy .

# building the package and check metadata
python3 -m pip install -e .[build]

python3 -m build
twine check --strict dist/*

# build documentation and check links ...
python3 -m pip install -e .[docs]

sphinx-build -b html docs dist/docs
sphinx-build -b linkcheck docs dist/docs
```


## Build documentation

```bash
python3 -m pip install -r ./docs/requirements.txt
# or 
python3 -m pip install -e .[docs]

sphinx-build -b html docs dist/docs
sphinx-build -b linkcheck docs dist/docs
```


## See also

- [clarin-eric/fcs-sru-server](https://github.com/clarin-eric/fcs-sru-server/)
- [clarin-eric/fcs-sru-client](https://github.com/clarin-eric/fcs-sru-client/)
