.. Copyright 2019 The Salish Sea MEOPAR contributors
.. and The University of British Columbia.
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..    http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.


.. _rpn-to-gemlamPackagedDevelopment:

****************************************
:kbd:`rpn-to-gemlam` Package Development
****************************************

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0
.. image:: https://img.shields.io/badge/python-3.6+-blue.svg
    :target: https://docs.python.org/3.7/
    :alt: Python Version
.. image:: https://img.shields.io/badge/version%20control-hg-blue.svg
    :target: https://bitbucket.org/salishsea/rpn-to-gemlam/
    :alt: Mercurial on Bitbucket
.. image:: https://img.shields.io/bitbucket/issues/salishsea/rpn-to-gemlam.svg
    :target: https://bitbucket.org/salishsea/rpn-to-gemlam/issues?status=new&status=open
    :alt: Issue Tracker

:command:`rpn-to-gemlam` is a tool for generating atmospheric forcing files for the
SalishSeaCast NEMO model from the ECCC 2007-2014 archival GEMLAM files produced
by the experimental phase of the HRPDS model.


.. _moad_toolsPythonVersions:

Python Versions
===============

.. image:: https://img.shields.io/badge/python-3.6+-blue.svg
    :target: https://docs.python.org/3.7/
    :alt: Python Version

The :command:`rpn-to-gemlam` package is developed and tested using `Python`_ 3.6 or later.
The package uses some Python language features that are not available in versions prior to 3.6,
in particular:

* `formatted string literals`_
  (aka *f-strings*)
* the `file system path protocol`_

.. _Python: https://www.python.org/
.. _formatted string literals: https://docs.python.org/3/reference/lexical_analysis.html#f-strings
.. _file system path protocol: https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
