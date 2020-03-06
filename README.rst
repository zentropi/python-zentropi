========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/zentropi/badge/?style=flat
    :target: https://readthedocs.org/projects/zentropi
    :alt: Documentation Status

.. |version| image:: https://img.shields.io/pypi/v/zentropi.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/zentropi

.. |wheel| image:: https://img.shields.io/pypi/wheel/zentropi.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/zentropi

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/zentropi.svg
    :alt: Supported versions
    :target: https://pypi.org/project/zentropi

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/zentropi.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/zentropi

.. |commits-since| image:: https://img.shields.io/github/commits-since/zentropi/python-zentropi/v2020.0.1.svg
    :alt: Commits since latest release
    :target: https://github.com/zentropi/python-zentropi/compare/v2020.0.1...master



.. end-badges

Zentropi Agent Framework: Script Your World

* Free software: BSD 3-Clause License

Installation
============

::

    pip install zentropi

You can also install the in-development version with::

    pip install https://github.com/zentropi/python-zentropi/archive/master.zip


Documentation
=============


https://zentropi.readthedocs.io/


Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
