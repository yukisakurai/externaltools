.. -*- mode: rst -*-

About
=====

``externaltools`` is a RootCore alternative that uses the
`waf build system <https://code.google.com/p/waf/>`_.

``externaltools`` also makes it easier to manage bundles of packages and builds
a Python package under which each tool is a subpackage.

Each bundle in bundles/ contains a list of the packages and the format of each
line is as follows::

   [package name] [path to package (trunk, or a specific tag or branch) in svn]

Please add any additional packages.


Getting and Building the External Tools
=======================================

To checkout all packages (supply your CERN username)::

   ./repo fetch -u username 2011 2012

Then build everything::

   make


Using the Packages
==================

First source the setup script::

   source externaltools/setup.sh

This adds externaltools/lib to the LD_LIBRARY_PATH and the parent directory of
externaltools to the PYTHONPATH.

In a Python script::

   from externaltools import MissingETUtility


Notes
=====

The EmbeddedCorrections package requires downloading the following file
separately since it is too large for svn and placing it in the
share directory::

   /afs/cern.ch/user/l/lhelary/public/TriggerEventNumberDimuons7TeV.root
