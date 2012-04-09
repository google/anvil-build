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
if sys.version_info < (2, 6, 0):
  raise RuntimeError('Python 2.6.0 or higher required')


install_requires = [
    'argparse>=1.2.1',
    'autobahn>=0.5.1',
    'glob2>=0.3',
    'networkx>=1.6',
    'Sphinx>=1.1.3',
    'watchdog>=0.6',
    ]
tests_require = [
    'coverage>=3.5.1',
    'unittest2>=0.5.1',
    ]


setup(
    name='Anvil',
    version='0.0.1dev',
    url='https://github.com/benvanik/anvil-build/',
    download_url='https://github.com/benvanik/anvil-build/tarball/master',
    license='Apache',
    author='Ben Vanik',
    author_email='benvanik@google.com',
    description='A parallel build system and content pipeline',
    long_description=__doc__,
    platforms='any',
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        },
    packages=['anvil',],
    test_suite='anvil.test.collector',
    include_package_data=True,
    zip_safe=True,
    entry_points = {
        'console_scripts': [
            'anvil = anvil.manage:main',
            ],
        },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        ])

