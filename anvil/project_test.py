#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the project module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

from anvil.module import *
from anvil.rule import *
from anvil.project import *
from anvil.test import FixtureTestCase


class ProjectTest(unittest2.TestCase):
  """Behavioral tests of Project rule handling."""

  def testEmptyProject(self):
    project = Project()
    self.assertIsNone(project.get_module(':a'))
    self.assertEqual(len(project.module_list()), 0)
    self.assertEqual(len(list(project.module_iter())), 0)

  def testProjectName(self):
    project = Project()
    self.assertNotEqual(len(project.name), 0)
    project = Project(name='a')
    self.assertEqual(project.name, 'a')

  def testProjectRuleNamespace(self):
    project = Project()
    self.assertIsNotNone(project.rule_namespace)
    rule_namespace = RuleNamespace()
    project = Project(rule_namespace=rule_namespace)
    self.assertIs(project.rule_namespace, rule_namespace)

  def testProjectModuleInit(self):
    module_a = Module('ma', rules=[Rule('a')])
    module_b = Module('mb', rules=[Rule('b')])
    module_list = [module_a, module_b]
    project = Project(modules=module_list)
    self.assertIsNot(project.module_list(), module_list)
    self.assertEqual(len(project.module_list()), len(module_list))
    self.assertIs(project.get_module('ma'), module_a)
    self.assertIs(project.get_module('mb'), module_b)

  def testAddModule(self):
    module_a = Module('ma', rules=[Rule('a')])
    module_b = Module('mb', rules=[Rule('b')])

    project = Project()
    self.assertIsNone(project.get_module('ma'))
    self.assertIsNone(project.get_module('mb'))
    self.assertEqual(len(project.module_list()), 0)

    project.add_module(module_a)
    self.assertIs(project.get_module('ma'), module_a)
    self.assertEqual(len(project.module_list()), 1)
    self.assertEqual(len(list(project.module_iter())), 1)
    self.assertEqual(project.module_list()[0], module_a)
    self.assertEqual(list(project.module_iter())[0], module_a)
    self.assertIsNone(project.get_module('mb'))

    project.add_module(module_b)
    self.assertIs(project.get_module('mb'), module_b)
    self.assertEqual(len(project.module_list()), 2)
    self.assertEqual(len(list(project.module_iter())), 2)

    with self.assertRaises(KeyError):
      project.add_module(module_b)
    self.assertEqual(len(project.module_list()), 2)

  def testAddModules(self):
    module_a = Module('ma', rules=[Rule('a')])
    module_b = Module('mb', rules=[Rule('b')])
    module_list = [module_a, module_b]

    project = Project()
    self.assertIsNone(project.get_module('ma'))
    self.assertIsNone(project.get_module('mb'))
    self.assertEqual(len(project.module_list()), 0)

    project.add_modules(module_list)
    self.assertIsNot(project.module_list(), module_list)
    self.assertEqual(len(project.module_list()), len(module_list))
    self.assertIs(project.get_module('ma'), module_a)
    self.assertIs(project.get_module('mb'), module_b)

    with self.assertRaises(KeyError):
      project.add_module(module_b)
    self.assertEqual(len(project.module_list()), len(module_list))
    with self.assertRaises(KeyError):
      project.add_modules([module_b])
    self.assertEqual(len(project.module_list()), len(module_list))
    with self.assertRaises(KeyError):
      project.add_modules(module_list)
    self.assertEqual(len(project.module_list()), len(module_list))

  def testGetModule(self):
    module_a = Module('ma', rules=[Rule('a')])
    module_b = Module('mb', rules=[Rule('b')])
    project = Project(modules=[module_a, module_b])

    self.assertIs(project.get_module('ma'), module_a)
    self.assertIs(project.get_module('mb'), module_b)
    self.assertIsNone(project.get_module('mx'))

  def testResolveRule(self):
    rule_a = Rule('a')
    rule_b = Rule('b')
    module_a = Module('ma', rules=[rule_a])
    module_b = Module('mb', rules=[rule_b])
    project = Project(modules=[module_a, module_b])

    with self.assertRaises(NameError):
      project.resolve_rule('')
    with self.assertRaises(NameError):
      project.resolve_rule('a')
    with self.assertRaises(NameError):
      project.resolve_rule('a/b/c')
    with self.assertRaises(NameError):
      project.resolve_rule('a', requesting_module=module_a)

    self.assertIs(project.resolve_rule(':a', requesting_module=module_a),
                  rule_a)
    self.assertIs(project.resolve_rule(':b', requesting_module=module_b),
                  rule_b)
    self.assertIs(project.resolve_rule('ma:a', requesting_module=module_a),
                  rule_a)
    self.assertIs(project.resolve_rule('mb:b', requesting_module=module_b),
                  rule_b)
    self.assertIs(project.resolve_rule('mb:b', requesting_module=module_a),
                  rule_b)
    self.assertIs(project.resolve_rule('ma:a', requesting_module=module_b),
                  rule_a)

  def testModuleResolver(self):
    rule_a = Rule('a')
    rule_b = Rule('b')
    module_a = Module('ma', rules=[rule_a])
    module_b = Module('mb', rules=[rule_b])
    module_resolver = StaticModuleResolver([module_a, module_b])
    project = Project(module_resolver=module_resolver)

    self.assertEqual(len(project.module_list()), 0)
    self.assertIs(project.resolve_rule('ma:a'), rule_a)
    self.assertEqual(len(project.module_list()), 1)
    self.assertIs(project.resolve_rule('mb:b'), rule_b)
    self.assertEqual(len(project.module_list()), 2)

    with self.assertRaises(IOError):
      project.resolve_rule('mx:x')

  def testRelativeModuleResolver(self):
    rule_a = Rule('a')
    rule_b = Rule('b')
    module_a = Module('ma', rules=[rule_a])
    module_b = Module('b/mb', rules=[rule_b])
    module_resolver = StaticModuleResolver([module_a, module_b])
    project = Project(module_resolver=module_resolver)

    self.assertEqual(len(project.module_list()), 0)
    with self.assertRaises(IOError):
        project.resolve_rule('ma:a', requesting_module=module_b)
    self.assertIs(project.resolve_rule('../ma:a',
                                       requesting_module=module_b), rule_a)
    self.assertIs(project.resolve_rule('b/mb:b',
                                       requesting_module=module_a), rule_b)


class FileModuleResolverTest(FixtureTestCase):
  """Behavioral tests for FileModuleResolver."""
  fixture = 'resolution'

  def testResolverInit(self):
    FileModuleResolver(self.root_path)

    with self.assertRaises(IOError):
      FileModuleResolver(os.path.join(self.root_path, 'x'))

  def testResolveModulePath(self):
    module_resolver = FileModuleResolver(self.root_path)

    self.assertEqual(module_resolver.resolve_module_path('BUILD'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('./BUILD'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('.'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('./a/..'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('./a/../BUILD'),
                     os.path.join(self.root_path, 'BUILD'))

    self.assertEqual(module_resolver.resolve_module_path('BUILD', 'a'),
                     os.path.join(self.root_path, 'a', 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('.', 'a'),
                     os.path.join(self.root_path, 'a', 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('..', 'a'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('../.', 'a'),
                     os.path.join(self.root_path, 'BUILD'))
    self.assertEqual(module_resolver.resolve_module_path('../BUILD', 'a'),
                     os.path.join(self.root_path, 'BUILD'))

    with self.assertRaises(IOError):
      module_resolver.resolve_module_path('empty')

  @unittest2.skipIf(sys.platform.startswith('win'), 'platform')
  def testNonFsResolution(self):
    module_resolver = FileModuleResolver(self.root_path)

    with self.assertRaises(IOError):
      module_resolver.resolve_module_path('/dev/null')

  def testFileResolution(self):
    module_resolver = FileModuleResolver(self.root_path)

    project = Project(module_resolver=module_resolver)
    self.assertEqual(len(project.module_list()), 0)
    root_rule = project.resolve_rule('.:root_rule')
    self.assertIsNotNone(root_rule)
    self.assertEqual(len(project.module_list()), 1)

  def testModuleNameMatching(self):
    module_resolver = FileModuleResolver(self.root_path)

    project = Project(module_resolver=module_resolver)
    self.assertEqual(len(project.module_list()), 0)
    rule_a = project.resolve_rule('a:rule_a')
    self.assertIsNotNone(rule_a)
    self.assertEqual(len(project.module_list()), 1)
    self.assertIs(rule_a, project.resolve_rule('a/BUILD:rule_a'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIs(rule_a, project.resolve_rule('a/../a/BUILD:rule_a'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIs(rule_a, project.resolve_rule('b/../a/BUILD:rule_a'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIs(rule_a, project.resolve_rule('b/../a:rule_a'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIsNotNone(project.resolve_rule('b:rule_b'))
    self.assertEqual(len(project.module_list()), 2)

  def testValidModulePaths(self):
    module_resolver = FileModuleResolver(self.root_path)

    test_paths = [
      ':root_rule',
      '.:root_rule',
      './:root_rule',
      './BUILD:root_rule',
      'a:rule_a',
      'a/BUILD:rule_a',
      'a/../a/BUILD:rule_a',
      'b/../a/BUILD:rule_a',
      'b/../a:rule_a',
      'a/.:rule_a',
      'a/./BUILD:rule_a',
      'b:rule_b',
      'b/:rule_b',
      'b/BUILD:rule_b',
      'b/c:rule_c',
      'b/c/build_file.py:rule_c_file',
    ]
    for test_path in test_paths:
      project = Project(module_resolver=module_resolver)
      self.assertIsNotNone(project.resolve_rule(test_path))
      self.assertEqual(len(project.module_list()), 1)

  def testInvalidModulePaths(self):
    module_resolver = FileModuleResolver(self.root_path)

    invalid_test_paths = [
      '.',
      '/',
    ]
    for test_path in invalid_test_paths:
      project = Project(module_resolver=module_resolver)
      with self.assertRaises(NameError):
        project.resolve_rule(test_path)
      self.assertEqual(len(project.module_list()), 0)

  def testMissingModules(self):
    module_resolver = FileModuleResolver(self.root_path)

    project = Project(module_resolver=module_resolver)
    with self.assertRaises(OSError):
      project.resolve_rule('x:rule_x')
    self.assertEqual(len(project.module_list()), 0)

    project = Project(module_resolver=module_resolver)
    with self.assertRaises(OSError):
      project.resolve_rule('/x:rule_x')
    self.assertEqual(len(project.module_list()), 0)

    project = Project(module_resolver=module_resolver)
    with self.assertRaises(OSError):
      project.resolve_rule('/BUILD:root_rule')
    self.assertEqual(len(project.module_list()), 0)

  def testMissingRules(self):
    module_resolver = FileModuleResolver(self.root_path)

    project = Project(module_resolver=module_resolver)
    self.assertEqual(len(project.module_list()), 0)
    self.assertIsNone(project.resolve_rule('.:x'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIsNone(project.resolve_rule('.:y'))
    self.assertEqual(len(project.module_list()), 1)

    project = Project(module_resolver=module_resolver)
    self.assertEqual(len(project.module_list()), 0)
    self.assertIsNone(project.resolve_rule('a:rule_x'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIsNone(project.resolve_rule('a/../a/BUILD:rule_x'))
    self.assertEqual(len(project.module_list()), 1)
    self.assertIsNone(project.resolve_rule('a/../a/BUILD:rule_y'))
    self.assertEqual(len(project.module_list()), 1)


if __name__ == '__main__':
  unittest2.main()
