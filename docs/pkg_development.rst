.. Copyright 2019-2020 The Salish Sea MEOPAR contributors
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
.. image:: https://img.shields.io/badge/python-3.7-blue.svg
    :target: https://docs.python.org/3.7/
    :alt: Python Version
.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/rpn-to-gemlam
    :alt: Git on GitHub
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter
.. image:: https://readthedocs.org/projects/rpn-to-gemlam/badge/?version=latest
    :target: https://rpn-to-gemlam.readthedocs.io/en/latest/
    :alt: Documentation Status
.. image:: https://img.shields.io/github/issues/SalishSeaCast/rpn-to-gemlam?logo=github
    :target: https://github.com/SalishSeaCast/rpn-to-gemlam/issues
    :alt: Issue Tracker

:command:`rpn-to-gemlam` is a tool for generating atmospheric forcing files for the
SalishSeaCast NEMO model from the ECCC 2007-2014 archival GEMLAM files produced
by the experimental phase of the HRPDS model.


.. _rpn-to-gemlamPythonVersions:

Python Versions
===============

.. image:: https://img.shields.io/badge/python-3.7-blue.svg
    :target: https://docs.python.org/3.7/
    :alt: Python Version

The :command:`rpn-to-gemlam` package is developed and tested using `Python`_ 3.7.
The package uses some Python language features that are not available in versions prior to 3.6,
in particular:

* `formatted string literals`_
  (aka *f-strings*)
* the `file system path protocol`_

.. _Python: https://www.python.org/
.. _formatted string literals: https://docs.python.org/3/reference/lexical_analysis.html#f-strings
.. _file system path protocol: https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519


.. _rpn-to-gemlamGettingTheCode:

Getting the Code
================

.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/rpn-to-gemlam
    :alt: Git on GitHub

Clone the code and documentation `repository`_,
and the `tools repository`_ from Bitbucket with:

.. _repository: https://github.com/SalishSeaCast/rpn-to-gemlam
.. _tools repository: https://bitbucket.org/salishsea/tools

.. code-block:: bash

    $ git clone git@github.com:SalishSeaCast/rpn-to-gemlam.git
    $ hg clone ssh://hg@bitbucket.org/salishsea/tools

or

.. code-block:: bash

    $ git clone https://github.com/SalishSeaCast/rpn-to-gemlam.git
    $ hg clone https://your-userid@bitbucket.org/salishsea/tools

if you don't have `ssh key authentication`_ set up on GitHub.

.. _ssh key authentication: https://help.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh


.. _rpn-to-gemlamDevelopmentEnvironment:

Development Environment
=======================

Setting up an isolated development environment using `Conda`_ is recommended.
Assuming that you have `Anaconda Python Distribution`_ or `Miniconda3`_ installed,
you can create and activate an environment called :kbd:`rpn-to-gemlam` that will have all of the Python packages necessary for development,
testing,
and building the documentation with the commands:

.. _Conda: https://conda.io/en/latest/
.. _Anaconda Python Distribution: https://www.anaconda.com/distribution/
.. _Miniconda3: https://conda.io/en/latest/miniconda.html

.. code-block:: bash

    $ cd rpn-to-gemlam
    $ conda env create -f env/environment-dev.yaml
    $ conda activate rpn-to-gemlam
    (rpn-to-gemlam)$ python3 -m  pip install --editable ../tools/SalishSeaTools
    (rpn-to-gemlam)$ python3 -m  pip install --editable .

The :kbd:`--editable` option in the :command:`pip install` command above installs the :kbd:`rpn_to_gemlam` package from the cloned repo via symlinks so that the installed :kbd:`rpn_to_gemlam` package will be automatically updated as the repo evolves.

To deactivate the environment use:

.. code-block:: bash

    (rpn-to-gemlam)$ conda deactivate


.. _rpn-to-gemlamCodingStyle:

Coding Style
============

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter

The :kbd:`NEMO_Nowcast` package uses the `black`_ code formatting tool to maintain a coding style that is very close to `PEP 8`_.

.. _black: https://black.readthedocs.io/en/stable/
.. _PEP 8: https://www.python.org/dev/peps/pep-0008/

:command:`black` is installed as part of the :ref:`rpn-to-gemlamDevelopmentEnvironment` setup.

To run :command:`black` on the entire code-base use:

.. code-block:: bash

    $ cd NEMO_Nowcast
    $ conda activate nemo-nowcast
    (nemo-nowcast)$ black ./

in the repository root directory.
The output looks something like::

  reformatted /media/doug/warehouse/MEOPAR/rpn-to-gemlam/docs/conf.py
  All done! ✨ 🍰 ✨
  1 file reformatted, 3 files left unchanged.


.. _rpn-to-gemlamDocumentation:

Documentation
=============

.. image:: https://readthedocs.org/projects/rpn-to-gemlam/badge/?version=latest
    :target: https://rpn-to-gemlam.readthedocs.io/en/latest/
    :alt: Documentation Status

The ::kbd:`rpn-to-gemlam` documentation is written in `reStructuredText`_ and converted to HTML using `Sphinx`_.

.. _reStructuredText: http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: http://www.sphinx-doc.org/en/master/

If you have write access to the `repository`_ on Bitbucket,
whenever you push changes to Bitbucket the documentation is automatically re-built and rendered at https://rpn-to-gemlam.readthedocs.io/en/latest/.

Additions,
improvements,
and corrections to these docs are *always* welcome.

The quickest way to fix typos, etc. on existing pages is to use the :guilabel:`Edit on GitHub` link in the upper right corner of the page to get to the online editor for the page on `GitHub`_.

.. _GitHub: https://github.com/SalishSeaCast/salishsea-site

For more substantial work,
and to add new pages,
follow the instructions in the :ref:`rpn-to-gemlamDevelopmentEnvironment` section above.
In the development environment you can build the docs locally instead of having to push commits to Bitbucket to trigger a `build on readthedocs.org`_ and wait for it to complete.
Below are instructions that explain how to:

.. _build on readthedocs.org: https://readthedocs.org/projects/rpn-to-gemlam/builds/

* build the docs with your changes,
  and preview them in Firefox

* check the docs for broken links


.. _rpn-to-gemlamBuildingAndPreviewingTheDocumentation:

Building and Previewing the Documentation
-----------------------------------------

Building the documentation is driven by the :file:`docs/Makefile`.
With your :kbd:`rpn-to-gemlam` environment activated,
use:

.. code-block:: bash

    (rpn-to-gemlam)$ cd rpn-to-gemlam/docs/
    (rpn-to-gemlam) docs$ make clean html

to do a clean build of the documentation.
The output looks something like::

  Removing everything under '_build'...
  Running Sphinx v1.8.5
  making output directory...
  loading intersphinx inventory from https://docs.python.org/objects.inv...
  intersphinx inventory has moved: https://docs.python.org/objects.inv -> https://docs.python.org/3/objects.inv
  building [mo]: targets for 0 po files that are out of date
  building [html]: targets for 2 source files that are out of date
  updating environment: 2 added, 0 changed, 0 removed
  reading sources... [100%] pkg_development
  looking for now-outdated files... none found
  pickling environment... done
  checking consistency... done
  preparing documents... done
  writing output... [100%] pkg_development
  generating indices... genindex
  writing additional pages... search
  copying static files... done
  copying extra files... done
  dumping search index in English (code: en) ... done
  dumping object inventory... done
  build succeeded.

The HTML rendering of the docs ends up in :file:`docs/_build/html/`.
You can open the :file:`index.html` file in that directory tree in your browser to preview the results of the build.
To preview in Firefox from the command-line you can do:

.. code-block:: bash

    (rpn-to-gemlam) docs$ firefox _build/html/index.html

If you have write access to the `repository`_ on Bitbucket,
whenever you push changes to Bitbucket the documentation is automatically re-built and rendered at https://rpn-to-gemlam.readthedocs.io/en/latest/.


.. _rpn-to-gemlamLinkCheckingTheDocumentation:

Link Checking the Documentation
-------------------------------

Sphinx also provides a link checker utility which can be run to find broken or redirected links in the docs.
With your :kbd:`rpn-to-gemlam` environment activated,
use:

.. code-block:: bash

    (rpn-to-gemlam)$ cd rpn-to-gemlam/docs/
    (rpn-to-gemlam) docs$ make linkcheck

The output looks something like::

  Running Sphinx v1.8.5
  making output directory...
  loading pickled environment... done
  building [mo]: targets for 0 po files that are out of date
  building [linkcheck]: targets for 2 source files that are out of date
  updating environment: 0 added, 0 changed, 0 removed
  looking for now-outdated files... none found
  preparing documents... done
  writing output... [ 50%] index
  (line   43) ok        https://www.apache.org/licenses/LICENSE-2.0
  writing output... [100%] pkg_development
  (line   21) ok        https://docs.python.org/3.7/
  (line   56) ok        https://www.python.org/
  (line   60) ok        https://docs.python.org/3/reference/lexical_analysis.html#f-strings
  (line   62) ok        https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep519
  (line   21) ok        https://black.readthedocs.io/en/stable/
  (line   21) ok        https://rpn-to-gemlam.readthedocs.io/en/latest/
  (line   92) ok        https://confluence.atlassian.com/bitbucket/set-up-an-ssh-key-728138079.html
  (line   21) ok        https://bitbucket.org/salishsea/rpn-to-gemlam/issues?status=new&status=open
  (line  102) ok        https://www.anaconda.com/distribution/
  (line   21) ok        https://bitbucket.org/salishsea/rpn-to-gemlam/
  (line  137) ok        https://www.python.org/dev/peps/pep-0008/
  (line  102) ok        https://conda.io/en/latest/
  (line  102) ok        https://conda.io/en/latest/miniconda.html
  (line  169) ok        http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
  (line  169) ok        http://www.sphinx-doc.org/en/master/
  (line   72) ok        https://bitbucket.org/salishsea/rpn-to-gemlam/
  (line   78) ok        https://bitbucket.org/salishsea/rpn-to-gemlam
  (line  174) ok        https://bitbucket.org/salishsea/rpn-to-gemlam
  (line  185) ok        https://readthedocs.org/projects/rpn-to-gemlam/builds/
  (line  246) ok        https://bitbucket.org/salishsea/rpn-to-gemlam

  build succeeded.

  Look for any errors in the above output or in _build/linkcheck/output.txt


.. _rpn-to-gemlamVersionControlRepository:

Version Control Repository
==========================

.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/rpn-to-gemlam
    :alt: Git on GitHub

The :kbd:`rpn-to-gemlam` code and documentation source files are available in the :kbd:`rpn-to-gemlam` `Git`_ repository at https://github.com/SalishSeaCast/rpn-to-gemlam.

.. _git: https://git-scm.org/


.. _rpn-to-gemlamIssueTracker:

Issue Tracker
=============

.. image:: https://img.shields.io/github/issues/SalishSeaCast/rpn-to-gemlam?logo=github
    :target: https://github.com/SalishSeaCast/rpn-to-gemlam/issues
    :alt: Issue Tracker

Development tasks,
bug reports,
and enhancement ideas are recorded and managed in the issue tracker at https://github.com/SalishSeaCast/rpn-to-gemlam/issues.


License
=======

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0

The code and documentation of the ``rpn-to-gemlam`` tool for
generating SalishSeaCast NEMO atmospheric forcing files from ECCC RPN
files are copyright 2019-2020 by the `Salish Sea MEOPAR Project Contributors`_ and The University of British Columbia.

.. _Salish Sea MEOPAR Project Contributors: https://github.com/SalishSeaCast/docs/blob/master/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
