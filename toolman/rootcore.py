"""
PACKAGE: The name of the package.
This has to match the directory name of your package.
If it doesn't match RootCore will generate an error during find_packages.sh.

PACKAGE_PRELOAD: A list of all the external libraries this package depends on.
Popular choices here include Hist and Tree, which will add
the root libraries for histogram and n-tuple processing.

PACKAGE_DEP: A list of all the RootCore packages your package depends on.
Listing a package here achieves two purposes: It generates an error if the
package is not present and it ensures the other package is compiled before this one.

PACKAGE_TRYDEP: Same as PACKAGE_DEP, only that it
doesn't generate an error if a package is missing.
This is mainly useful in conjunction with package auto-configuration (see section below).

PACKAGE_CLEAN: A list of files that should be deleted when object
files are removed. This is normally not necessary.

PACKAGE_NOOPT: If this is set to 1, the compiler optimizations are turned
off for this package. This is normally not necessary, but there
are some cases where compiler optimizations cause an unacceptable delay during compilation.

PACKAGE_NOCC: If this is set to 1, no library will be generated
for this package. This is mainly useful if the package only
consists of a collection of header files,
or is a front-end for including a third-party library.

PACKAGE_CXXFLAGS: Extra compilation flags for this package.

PACKAGE_OBJFLAGS: Same as above, but these flags also get
propagated to all packages that depend on this one.

PACKAGE_LDFLAGS Same as above, but for linker flags.

PACKAGE_BINFLAGS: Same as above, but for linker flags.
"""
from utils import memoized
import subprocess
import os
import packages


MAKEFILE = 'Makefile.RootCore'


def read_makefile(makefile):
    make = {}
    for i, line in enumerate(open(makefile).readlines()):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('include'):
            continue
        try:
            name, value = line.split('=')
            name = name.strip()
            if '#' in value:
                # ignore inline comments
                value = value[:value.index('#')]
            value = value.strip()
            if value == '':
                continue
            if value in ('0', '1'):
                value = bool(int(value))
            make[name] = value
        except:
            print "%s: line %i not understood: %s" % (makefile, i + 1, line)
    return make


def define_env(env, make):
    if 'PACKAGE_CXXFLAGS' in make:
        env.append_value('CXXFLAGS', make['PACKAGE_CXXFLAGS'].split())
    if 'PACKAGE_LDFLAGS' in make:
        if 'root-config' not in make['PACKAGE_LDFLAGS']:
            env.append_value('LINKFLAGS', make['PACKAGE_LDFLAGS'].split())
    if 'PACKAGE_PRELOAD' in make:
        libs = make['PACKAGE_PRELOAD'].split()
        linkflags = ['-l%s' % lib for lib in libs]
        env.append_value('LINKFLAGS', linkflags)


@memoized
def root_inc():
    return subprocess.Popen(
        ['root-config', '--incdir'],
        stdout=subprocess.PIPE).communicate()[0].strip().split()


@memoized
def root_linkerflags():
    return (subprocess.Popen(
        ['root-config', '--libs', '--ldflags'],
        stdout=subprocess.PIPE).communicate()[0].strip().split() +
        ['-lXMLParser'])


@memoized
def root_cflags():
    return subprocess.Popen(
        ['root-config', '--cflags'],
        stdout=subprocess.PIPE).communicate()[0].strip().split()


@memoized
def root_exec():
    return subprocess.Popen(
        ['root-config', '--exec-prefix'],
        stdout=subprocess.PIPE).communicate()[0].strip()


@memoized
def root_libdir():
    return subprocess.Popen(
        ['root-config', '--libdir'],
        stdout=subprocess.PIPE).communicate()[0].strip()


def find_linkdef(base='.'):
    for dirpath, dirnames, filenames in os.walk(base):
        for filename in filenames:
            if filename.lower() == 'linkdef.h':
                return os.path.join(dirpath, filename)
    return None


def is_rootcore(bundle, name):
    path = os.path.join(packages.PACKAGE_PATH, bundle, name)
    return (os.path.isdir(os.path.join(path, 'Root')) and
            os.path.isdir(os.path.join(path, name)) and
            os.path.isfile(os.path.join(path, 'cmt', MAKEFILE)))
