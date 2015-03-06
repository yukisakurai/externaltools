# this is generated code
import ROOT
import os
from {depth} import ResourceNotFound
from {depth} import load_package


HERE = os.path.dirname(os.path.abspath(__file__))
NAME = '{package.dot_versioned_name}'
BUNDLE = '{bundle}'

# read dependencies
DEPS = []
deps_file = open(os.path.join(HERE, 'deps'), 'r')
for dep in deps_file.readlines():
    DEPS.append(dep.strip().split())
deps_file.close()

load_package(BUNDLE, NAME, DEPS)

RESOURCE_PATH = os.path.join(
    HERE, 'share') + os.path.sep


def get_resource(name=''):

    path = os.path.join(RESOURCE_PATH, name)
    if os.path.exists(path):
        return path
    raise ResourceNotFound('resource %s not found in package %s' %
        (name, __name__))

