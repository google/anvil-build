#!/usr/bin/env python

# Copyright 2012 Google Inc. All Rights Reserved.

"""
Anvil
-----

A parallel build system and content pipeline.

"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import sys
from setuptools import setup


# Require Python 2.6+
if sys.version_info < (2, 6):
  raise RuntimeError('Python 2.6 or higher required')


# Pull from the version py
import anvil.version
VERSION = anvil.version.VERSION_STR

CLASSIFIERS = [
    'Development Status :: 2 - Pre-Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Software Development :: Build Tools',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Utilities',
    ]

INSTALL_REQUIRES = [
    'argparse>=1.2.1',
    'autobahn>=0.5.1',
    'glob2>=0.3',
    'networkx>=1.6',
    'Sphinx>=1.1.3',
    'watchdog>=0.6',
    ]

TESTS_REQUIRE = [
    'coverage>=3.5.1',
    'unittest2>=0.5.1',
    ]


setup(
    name='anvil-build',
    version=VERSION,
    author='Ben Vanik',
    author_email='benvanik@google.com',
    description='A parallel build system and content pipeline',
    long_description=__doc__,
    classifiers=CLASSIFIERS,
    url='https://github.com/benvanik/anvil-build/',
    download_url='https://github.com/benvanik/anvil-build/tarball/master#egg=anvil-build',
    license='Apache License 2.0',
    platforms='any',
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    extras_require={
        'test': TESTS_REQUIRE,
        },
    packages=[
        'anvil',
        'anvil.commands',
        'anvil.rules',
        ],
    include_package_data=True,
    package_data={
        'anvil.commands': ['*_command.py'],
        'anvil.rules': ['*_rules.py'],
        },
    test_suite='anvil.test.collector',
    # We dynamically load command/rule py files - would need to use
    # pkg_resources or something else to be zip safe
    # http://www.no-ack.org/2010/09/including-data-files-into-python.html
    zip_safe=False,
    entry_points = {
        'console_scripts': [
            'anvil = anvil.manage:main',
            ],
        })

