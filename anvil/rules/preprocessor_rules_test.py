#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the preprocessor_rules module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

from anvil.context import BuildContext, BuildEnvironment, Status
from anvil.project import FileModuleResolver, Project
from anvil.test import FixtureTestCase, RuleTestCase
from preprocessor_rules import *


class TemplateFilesRuleTest(RuleTestCase):
  """Behavioral tests of the TemplateFilesRule type."""
  fixture='preprocessor_rules/template_files'

  def setUp(self):
    super(TemplateFilesRuleTest, self).setUp()
    self.build_env = BuildEnvironment(root_path=self.root_path)

  def test(self):
    project = Project(module_resolver=FileModuleResolver(self.root_path))

    with BuildContext(self.build_env, project) as ctx:
      self.assertTrue(ctx.execute_sync([
          ':template_all',
          ':template_dep_2',
          ]))

      self.assertRuleResultsEqual(ctx,
          ':template_all', ['a.txt',
                            'dir/b.txt'],
          output_prefix='build-out')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/a.txt'),
          '123world456\n')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/dir/b.txt'),
          'b123world456\n')

      self.assertRuleResultsEqual(ctx,
          ':template_dep_1', ['a.nfo',
                              'dir/b.nfo'],
          output_prefix='build-out')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/a.nfo'),
          '123${arg2}456\n')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/dir/b.nfo'),
          'b123${arg2}456\n')

      self.assertRuleResultsEqual(ctx,
          ':template_dep_2', ['a.out',
                              'dir/b.out'],
          output_prefix='build-out')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/a.out'),
          '123world!456\n')
      self.assertFileContents(
          os.path.join(self.root_path, 'build-out/dir/b.out'),
          'b123world!456\n')


if __name__ == '__main__':
  unittest2.main()
