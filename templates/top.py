import os
import ROOT

import logging
log = logging.getLogger(__name__)


class ResourceNotFound(Exception):
    pass


LOADED_PACKAGES = {}
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'common'


def register_loaded(bundle, package):

    # check if this package was already loaded in another non-common bundle
    package_name = package.split('.')[0]
    for other_bundle, libs in LOADED_PACKAGES.items():
        if other_bundle in (bundle, NAME):
            continue
        for loaded_package in libs:
            if package_name == loaded_package.split('.')[0]:
                raise RuntimeError(
                    'Attempted to load the same package (%s) from two bundles' %
                    package_name)
    if bundle not in LOADED_PACKAGES:
        LOADED_PACKAGES[bundle] = []
    if package not in LOADED_PACKAGES[bundle]:
        LOADED_PACKAGES[bundle].append(package)
        return False
    return True


def load_package(bundle, package, deps=None):

    package_name = package.split('.')[0]
    # read the deps if not supplied
    if deps is None:
        deps = []
        if bundle == NAME:
            deps_file = open(
                os.path.join(HERE, package_name, 'deps'), 'r')
        else:
            deps_file = open(
                os.path.join(HERE, bundle, package_name, 'deps'), 'r')
        for dep in deps_file.readlines():
            deps.append(dep.strip().split())
        deps_file.close()

    # first recurse on dependencies
    for dep_bundle, dep in deps:
        load_package(dep_bundle, dep)

    if bundle == NAME:
        lib_path = os.path.join(
            HERE, 'lib', 'lib%s_%s.so' % (package, bundle))
    else:
        lib_path = os.path.join(
            HERE, bundle, 'lib', 'lib%s_%s.so' % (package, bundle))

    # ignore packages that didn't produce a library (headers only)
    if os.path.isfile(lib_path):
        if not register_loaded(bundle, package):
            log.info("loading %s/%s ..." %
                     (bundle, os.path.basename(lib_path)))
            ROOT.gSystem.Load(lib_path)


def report():

    log.info("Loaded packages:")
    for bundle, packages in LOADED_PACKAGES.items():
        for package in packages:
            log.info(package)
