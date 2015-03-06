#!/usr/bin/env python

from glob import glob
import os
from os.path import join
import sys
import shutil

from waflib import Build, Utils, TaskGen, Logs

import toolman
from toolman import rootcore


top = '.'
out = 'build'

init_template = open('templates/top.py').read()
bundle_init_template = open('templates/bundle.py').read()
package_init_template = open('templates/package.py').read()
setup_template = open('templates/setup.sh').read()

SPECIAL = ['TileTripReader']

def options(opt):

    opt.load('compiler_cxx')
    opt.add_option('--yall', default=False,
        help="answer yes to all questions")
    
    # Default the prefix to ${PWD}/externaltools
    prefix_option = opt.parser.get_option('--prefix')
    old_default = prefix_option.default
    new_default = join(os.path.abspath(os.curdir), 'externaltools')
    opt.parser.set_default('prefix', new_default)
    prefix_option.help = prefix_option.help.replace(old_default, new_default)


def configure(conf):
    
    conf.load('compiler_cxx')
    conf.env['CXXFLAGS'] = rootcore.root_cflags()[:]
    conf.env.append_value('CXXFLAGS', '-g')
    conf.env['LINKFLAGS'] = rootcore.root_linkerflags()[:]
    conf.env.append_value('LINKFLAGS', conf.env.CXXFLAGS)
    #conf.env['INCLUDES'] = rootcore.root_inc()[:]
    conf.find_program('root-config')
    conf.find_program('rootcint')


LIBRARY_DEPENDENCIES = {}


def build(bld):
            
    bld.load('compiler_cxx')
    if bld.cmd == 'install':
        if os.path.exists(bld.options.prefix):
            print "%s already exists." % bld.options.prefix
            if (not bld.options.yall and raw_input(
                "Its contents could be overwritten! Continue? Y/[n]: ")
                != 'Y'):
                return
        bld.add_post_fun(build_python_package)

    install_lib_path = join(bld.options.prefix, 'lib')
    #bld.post_mode = Build.POST_AT_ONCE
    bld.post_mode = Build.POST_LAZY
    #bld.post_mode = Build.POST_BOTH

    rootcint_cmd = (
        'rootcint -f ${TGT} -c -p ${CXXFLAGS} ${ROOTCINT_INCLUDES} ${SRC}; '
        'grep include ${SRC} > ${TGT}-tmp || true; '
        'cat ${TGT} >> ${TGT}-tmp; '
        'mv ${TGT}-tmp ${TGT}')
    partitioning = toolman.packages.get_partitioning()
    for bundle, packages in partitioning.items():
        
        if bundle not in LIBRARY_DEPENDENCIES:
            LIBRARY_DEPENDENCIES[bundle] = {}

        bld.env['PACKAGES_%s' % bundle] = packages
        
        bld.add_group('dicts_%s' % bundle)
        bld.add_group('libs_%s' % bundle)

        BUNDLE_PATH = join(toolman.packages.PACKAGE_DIR, bundle)

        for package in packages:
            name = package.name
            
            if name not in LIBRARY_DEPENDENCIES[bundle]:
                LIBRARY_DEPENDENCIES[bundle][name] = []
            
            PATH = join(BUNDLE_PATH, name)

            LIB_DEPENDS = []
            INCLUDES = []
            LINKFLAGS = []
            make = None
            if rootcore.is_rootcore(bundle, name):
                # parse Makefile.RootCore
                make = rootcore.read_makefile(
                        join(PATH, 'cmt', rootcore.MAKEFILE))
                SOURCES = bld.path.ant_glob(join(PATH, 'Root', '*.cxx'))
                HEADERS = bld.path.ant_glob(join(PATH, name, '*.h'))
                # check for dependencies on other packages
                if 'PACKAGE_DEP' in make and package.name not in SPECIAL:
                    DEPS = make['PACKAGE_DEP'].split()
                    for DEP in DEPS:
                        # search for DEP in this bundle
                        # and if not found look in common
                        dep_bundle = None
                        dep_package = None
                        for other_package in packages:
                            if DEP == other_package.name:
                                dep_bundle = bundle
                                dep_package = other_package
                        if dep_bundle is None and bundle != 'common':
                            # check in common
                            for other_package in partitioning['common']:
                                if DEP == other_package.name:
                                    dep_bundle = 'common'
                                    dep_package = other_package
                        if dep_bundle is None:
                            sys.exit('Package %s depends on %s '
                                     'but it is not present' % (name, DEP))
                        INCLUDES.append(
                            join(toolman.packages.PACKAGE_DIR,
                                 dep_bundle, DEP))
                        LIB_DEPENDS.append((dep_bundle, DEP))
                        LIBRARY_DEPENDENCIES[bundle][name].append(
                                (dep_bundle, dep_package))
            else:
                SOURCES = bld.path.ant_glob(join(PATH, 'src', '*.cxx'))
                if not SOURCES:
                    SOURCES = bld.path.ant_glob(join(PATH, '*.cxx'))
                HEADERS = bld.path.ant_glob(join(PATH, name, '*.h'))
                if not HEADERS:
                    HEADERS = bld.path.ant_glob(join(PATH, '*.h'))

            INCLUDES.append(PATH) 
            # possible improper includes in source files
            INCLUDES.append(join(PATH, name))
            INCLUDES.append(join(PATH, 'src'))
            
            DICT_SRC = None
            linkdef = rootcore.find_linkdef(PATH)
            if linkdef is not None:
                DICT = join(PATH, '%s_DICT' % name.upper())
                DICT_SRC = '%s.cxx' % DICT
                DICT_H = '%s.h' % DICT
                try:
                    HEADERS.remove(linkdef)
                except ValueError:
                    pass
                try:
                    HEADERS.remove(DICT_H)
                except ValueError:
                    pass
                try:
                    SOURCES.remove(DICT_SRC)
                except ValueError:
                    pass
                bld.set_group('dicts_%s' % bundle)
                rbld = bld(
                        rule=rootcint_cmd,
                        source=linkdef,
                        target=DICT_SRC)
                rbld.env.append_value('ROOTCINT_INCLUDES',
                        ' '.join(['-I../%s' % inc for inc in INCLUDES]))
                if make is not None:
                    rootcore.define_env(rbld.env, make)
                if package.name not in SPECIAL:
                    rbld.env.append_value('CXXFLAGS', '-DROOTCORE')
                else:
                    rbld.env.append_value('CXXFLAGS', '-D__STANDALONE__')
            
            bld.set_group('libs_%s' % bundle)
            if bundle == 'common':
                install_path = '${PREFIX}/lib'
            else:
                install_path = '${PREFIX}/%s/lib' % bundle
            
            shlib = bld.shlib(
                    source=SOURCES,
                    dynamic_source=DICT_SRC,
                    target=package.dot_versioned_name + "_%s" % bundle,
                    #use=LIB_DEPENDS,
                    install_path=install_path)
            
            if make is not None:
                rootcore.define_env(shlib.env, make)
            
            shlib.env.append_value('INCLUDES', INCLUDES)
            shlib.env.append_value('LINKFLAGS', LINKFLAGS)
            if package.name not in SPECIAL:
                shlib.env.append_value('CXXFLAGS', '-DROOTCORE')
            else:
                shlib.env.append_value('CXXFLAGS', '-D__STANDALONE__')
            shlib.env.append_value('LINKFLAGS', shlib.env.CXXFLAGS)


def ignore_paths(dir, contents):
    
    # ignore hidden files/dirs
    return filter(lambda c: c.startswith('.'), contents)


def build_python_package(bld):

    # create main __init__.py
    init_file = open(join(bld.options.prefix, '__init__.py'), 'w')
    init_file.write(init_template)
    init_file.close()
    
    # create setup.sh
    setup_file = open(join(bld.options.prefix, 'setup.sh'), 'w')
    setup_file.write(setup_template)
    setup_file.close()
    
    partitioning = toolman.packages.get_partitioning()
    for bundle, packages in partitioning.items():
        
        if bundle == 'common':
            depth = '..'
            base_bundle = bld.options.prefix
        else:
            depth = '...'
            base_bundle = join(
                    bld.options.prefix, bundle)
            if not os.path.exists(base_bundle):
                os.mkdir(base_bundle)
        
            # create bundle __init__.py
            bundle_init = open(join(base_bundle, '__init__.py'), 'w')
            bundle_init.write(bundle_init_template.format(**locals()))
            bundle_init.close()

        for package in bld.env['PACKAGES_%s' % bundle]:
            LIBRARY = 'lib%s.so' % package
            base_package = join(base_bundle, package.name)
            if not os.path.exists(base_package):
                os.mkdir(base_package)
            
            # create package-level __init__.py
            package_init_file = open(join(base_package, '__init__.py'), 'w')
            package_init_file.write(package_init_template.format(**locals()))
            package_init_file.close()
            
            # write dependencies file
            dep_file = open(join(base_package, 'deps'), 'w')
            for dep_bundle, dep in LIBRARY_DEPENDENCIES[bundle][package.name]:
                dep_file.write('%s %s\n' % (dep_bundle, dep.dot_versioned_name))
            dep_file.close()

            # copy data
            # check for either data/ or share/
            share_data = join(toolman.packages.PACKAGE_PATH, bundle, package.name, 'share')
            data_data = join(toolman.packages.PACKAGE_PATH, bundle, package.name, 'data')
            data = None
            
            if os.path.exists(share_data) and os.path.exists(data_data):
                Logs.warn("Both share/ and data/ exist for package %s! "
                          "Using data/" % package)
            
            if os.path.exists(data_data):
                data = data_data
            elif os.path.exists(share_data):
                data = share_data
            
            if data is not None:
                Logs.info("Copying data for package %s ..." % package)
                dest = join(base_package, 'share')
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(data, dest, ignore=ignore_paths)


# support for the "dynamic_source" attribute follows
@TaskGen.feature('cxx')
@TaskGen.before('process_source')
def dynamic_post(self):
    """
    bld(dynamic_source='*.cxx', ..) will search for source files to add
    to the attribute 'source' we could also call "eval" or whatever expression
    """
    if not getattr(self, 'dynamic_source', None):
        return
    self.source = Utils.to_list(self.source)
    src_nodes = self.path.get_bld().ant_glob(self.dynamic_source, quiet=True)
    self.source.extend(src_nodes)

    # if headers are created dynamically, assign signatures manually:
    #for x in self.path.get_bld().ant_glob('*.h'):
    #    x.sig = Utils.h_file(x.abspath())
    self.env.append_value('INCLUDES', [s.bld_dir() for s in src_nodes])
