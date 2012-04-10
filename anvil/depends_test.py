#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the depends module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

from depends import *


class DependencyTest(unittest2.TestCase):
  """Behavioral tests of the Dependency type."""

  def testNodeLibrary(self):
    # TODO(benvanik): test NodeLibrary
    NodeLibrary('glsl-unit')
    pass

  def testPythonLibrary(self):
    # TODO(benvanik): test PythonLibrary
    PythonLibrary('argparse')
    pass

  def testNativePackage(self):
    # TODO(benvanik): test NativePackage
    NativePackage()
    pass


class DependencyManagerTest(unittest2.TestCase):
  """Behavioral tests of the DependencyManager type."""

  def testScanDependencies(self):
    # TODO(benvanik): test scan_dependencies
    DependencyManager()
    pass

  def testInstallAll(self):
    # TODO(benvanik): test install_all
    DependencyManager()
    pass


if __name__ == '__main__':
  unittest2.main()
