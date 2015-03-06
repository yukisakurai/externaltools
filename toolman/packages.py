import os
import sys
import re
import shutil
import subprocess
import operator
import fileinput


PACKAGE_PATTERN = re.compile(
    '(?P<name>\w+)(?P<tag>(?:-\d{2}){3}(?:-\d{2})?)?')
TAG_PATTERN = re.compile(
    '-(?P<major>\d{2})'
    '-(?P<minor>\d{2})'
    '-(?P<micro>\d{2})'
    '(?:-(?P<branch>\d{2}))?')

BASE_FLAG = 'TOOLMAN_BASE'
if BASE_FLAG in os.environ:
    BASE_PREFIX = os.environ[BASE_FLAG]
else:
    # use parent directory
    BASE_PREFIX = os.path.abspath(
        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)), os.path.pardir))

SVNBASE = 'svn+ssh://{user}@svn.cern.ch/reps/'
PACKAGE_DIR = 'src'
BUNDLES_DIR = 'bundles'
PACKAGE_PATH = os.path.join(BASE_PREFIX, PACKAGE_DIR)
BUNDLES_PATH = os.path.join(BASE_PREFIX, BUNDLES_DIR)
REPOS_FILE = os.path.join(BASE_PREFIX, 'repo.lst')

if not os.path.exists(PACKAGE_PATH):
    os.mkdir(PACKAGE_PATH)


def read_file(name):
    base_path = os.path.dirname(name)
    file_stack = [fileinput.FileInput(name)]
    while file_stack:
        fp = file_stack[-1]
        line = fp.readline()
        if not line: # end of file
            file_stack[-1].close()
            file_stack.pop(-1)
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # include files
        tokens = line.split()
        if len(tokens) == 2 and tokens[0] == 'include':
            file_stack.append(
                fileinput.FileInput(os.path.join(base_path, tokens[1])))
        else:
            try:
                yield line
            except:
                print "line {0:d} of file {1} not understood: {2}".format(
                    fp.lineno(), fp.filename(), line)

REPO = {}
for line in read_file(REPOS_FILE):
    package = os.path.basename(line)
    path = os.path.dirname(line)
    if package in REPO:
        # package with the same name from different repositories
        curr_package = REPO[package]
        del REPO[package]
        REPO[curr_package] = curr_package
        REPO[line] = path
    else:
        REPO[package] = path


class Package(object):
    @classmethod
    def from_string(cls, package, base=None):
        match = re.match(PACKAGE_PATTERN, package)
        if not match:
            raise ValueError(
                "Not a valid package name: {0}".format(package))
        name = match.group('name')
        if base is None:
            if name not in REPO:
                raise ValueError(
                    "Package {0} not found in any "
                    "listed repositories".format(name))
            base = REPO[name]
        tag = None
        if match.group('tag'):
            tag = match.group('tag')
        return cls(name=name, base=base, tag=tag)

    def __init__(self, name, base, tag=None):
        self.base = base
        self.name = name
        self.tag = tag
        path_tokens = base.split(os.path.sep)
        self.repo = path_tokens[0]
        self.repo_path = os.path.join(*path_tokens[1:])
        self.web_url = 'https://svnweb.cern.ch/trac/{0}/browser/{1}/{2}'.format(
            self.repo, self.repo_path, name)
        if tag is not None:
            match = re.match(TAG_PATTERN, tag)
            if not match:
                raise ValueError("Tag {0} not understood".format(tag))
            self.version = map(int, match.groups(-1))
            if self.version[-1] == -1:
                self.version_str = '.'.join(map(str, self.version[:-1]))
            else:
                self.version_str = '.'.join(map(str, self.version))
            self.dot_versioned_name = '{0}.{1}'.format(
                self.name, self.version_str)
            self.path = os.path.normpath(
                os.path.join(base, name, 'tags', name + tag))
        else:
            self.version = None
            self.version_str = None
            self.dot_versioned_name = self.name
            self.path = os.path.join(base, name, 'trunk')

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self.path

    def __hash__(self):
        return hash((self.name, self.tag, self.path))

    def __eq__(self, other):
        return (self.name == other.name and
                self.tag == other.tag and
                self.path == other.path)

    def __cmp__(self, other):
        if self.name != other.name:
            raise ValueError(
                "Cannot compare different packages {0} and {1}".format(
                    self.name, other.name))
        if self.tag is None and other.tag is None:
            # both are trunk
            return 0
        elif self.tag is None and other.tag is not None:
            # trunk wins
            return 1
        elif self.tag is not None and other.tag is None:
            # trunk wins
            return -1
        # compare tags
        return cmp(self.version, other.version)


def read_packages(bundle):
    print "Reading packages in bundle {0} ...".format(bundle)
    for line in read_file(os.path.join(BUNDLES_DIR, '%s.lst' % bundle)):
        yield Package.from_string(*line.split())


def list_bundles():
    return [os.path.splitext(name)[0] for name in os.listdir(BUNDLES_DIR)
            if not name.startswith('.')]


def bundle_fetched(bundle):
    return os.path.isdir(os.path.join(PACKAGE_PATH, bundle))


def list_packages(bundle):
    return os.listdir(os.path.join(PACKAGE_PATH, bundle))


def list_tags(user, package):
    USER = user
    url = os.path.join(
        SVNBASE.format(**locals()), package.base, package.name, 'tags')
    tags = subprocess.Popen(['svn', 'list', url],
        stdout=subprocess.PIPE).communicate()[0].strip().split()
    return [Package.from_string(tag, package.base) for tag in tags]


def show_repo():
    for name, path in REPO.items():
        print "{0} => {1}".format(name, path)


def show_used(bundle):
    for package in read_packages(bundle):
        print "{0} => {1}".format(package.name, package.path)


def show_tags(user, package):
    for tag in list_tags(user, package):
        print tag


def show_updates(user, bundle):
    for package in read_packages(bundle):
        if package.tag is not None:
            # only look for updates if we are not using the trunk
            tags = list_tags(user, package)
            tags.sort()
            if package not in tags:
                print "Package {0} is not an available tag".format(package)
                continue
            newer_packages = tags[tags.index(package) + 1:]
            if newer_packages:
                print
                if len(newer_packages) == 1:
                    print "A newer tag of package %s is available:" % (
                        package.name)
                else:
                    print "Newer tags of package %s are available:" % (
                        package.name)
                print package.web_url
                for p in newer_packages:
                    print p.tag
                print "You are using %s" % package.tag
    print


def get_partitioning(bundles=None):
    """
    determine packages in common between bundles
    and for each package in the common packages that depends on a package that
    isn't in common between the bundles (different tags), count that package
    as being unique to each bundle. Repeat until no packages in the common
    packages depends on a package in the bundle-specific package collections.
    Return a dict mapping bundle names and 'common' (no bundle can be named
    'common') to packages.
    """
    if bundles is None:
        bundles = list_bundles()
    partitioning = {}
    for bundle in bundles:
        bundle_packages = set()
        for package in read_packages(bundle):
            for other_package in bundle_packages:
                # error if multiple packages with same name and possibly
                # different tags, so Package.__eq__ doesn't work here.
                if other_package.name == package.name:
                    raise NameError(
                        "Duplicate packages in bundle {0}: {1} {2}".format(
                            bundle, package, other_package))
            bundle_packages.add(package)
        partitioning[bundle_to_name(bundle)] = bundle_packages
    # determine largest common subset of packages between bundles
    # this is the intersection of all sets
    common_packages = reduce(operator.__and__, partitioning.values())
    # remove packages from each bundle that are common
    for bundle, bundle_packages in partitioning.items():
        bundle_packages.difference_update(common_packages)
    partitioning['common'] = common_packages
    return partitioning


def fetch(user, bundles):
    svnbase = SVNBASE.format(**locals())
    partitioning = get_partitioning(bundles)
    for bundle, packages in partitioning.items():
        for package in packages:
            url = os.path.join(svnbase, package.path)
            outpath = os.path.join(PACKAGE_PATH, bundle, package.name)
            print
            # update
            if os.path.exists(outpath):
                print "Updating {0} ...".format(package.name)
                print "This will remove and recreate {0}".format(outpath)
                if raw_input("Continue? (Y/[n]) ") == 'Y':
                    shutil.rmtree(outpath)
                    print
                else:
                    continue
            # checkout
            print "Checking out {0} ({1}) ...".format(
                package.name, package.path)
            if subprocess.call(['svn', 'co', url, outpath]):
                print "Failed to checkout {0}!".format(package.name)


def bundle_to_name(bundle):
    # Replace invalid characters with '_' and convert to lower case
    return 'bundle_{0}'.format(re.sub('[^0-9a-zA-Z_]', '_', bundle).lower())
