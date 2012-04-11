#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the graph module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import unittest2

from anvil.graph import *
from anvil.module import *
from anvil.rule import *
from anvil.project import *


class RuleGraphTest(unittest2.TestCase):
  """Behavioral tests of the RuleGraph type."""

  def setUp(self):
    super(RuleGraphTest, self).setUp()

    self.module_1 = Module('m1', rules=[
        Rule('a1'),
        Rule('a2'),
        Rule('a3'),
        Rule('b', srcs=[':a1', 'a/b/c'], deps=[':a2'],),
        Rule('c', deps=[':b'],),])
    self.module_2 = Module('m2', rules=[
        Rule('p', deps=['m1:c'],)])
    self.project = Project(modules=[self.module_1, self.module_2])

  def testConstruction(self):
    project = Project()
    graph = RuleGraph(project)
    self.assertIs(graph.project, project)

    project = self.project
    graph = RuleGraph(project)
    self.assertIs(graph.project, project)

  def testAddRulesFromModule(self):
    graph = RuleGraph(self.project)
    graph.add_rules_from_module(self.module_1)
    self.assertTrue(graph.has_rule('m1:a1'))
    self.assertTrue(graph.has_rule('m1:a2'))
    self.assertTrue(graph.has_rule('m1:a3'))
    self.assertTrue(graph.has_rule('m1:b'))
    self.assertTrue(graph.has_rule('m1:c'))
    self.assertFalse(graph.has_rule('m2:p'))
    graph.add_rules_from_module(self.module_2)
    self.assertTrue(graph.has_rule('m2:p'))

    graph = RuleGraph(self.project)
    graph.add_rules_from_module(self.module_2)
    self.assertTrue(graph.has_rule('m2:p'))
    self.assertTrue(graph.has_rule('m1:a1'))
    self.assertTrue(graph.has_rule('m1:a2'))
    self.assertFalse(graph.has_rule('m1:a3'))
    self.assertTrue(graph.has_rule('m1:b'))
    self.assertTrue(graph.has_rule('m1:c'))

  def testCycle(self):
    module = Module('mc', rules=[
        Rule('a', deps=[':b']),
        Rule('b', deps=[':a'])])
    project = Project(modules=[module])
    graph = RuleGraph(project)
    with self.assertRaises(ValueError):
      graph.add_rules_from_module(module)

    module_1 = Module('mc1', rules=[Rule('a', deps=['mc2:a'])])
    module_2 = Module('mc2', rules=[Rule('a', deps=['mc1:a'])])
    project = Project(modules=[module_1, module_2])
    graph = RuleGraph(project)
    with self.assertRaises(ValueError):
      graph.add_rules_from_module(module_1)

  def testHasRule(self):
    graph = RuleGraph(self.project)
    graph.add_rules_from_module(self.module_1)
    self.assertTrue(graph.has_rule('m1:a1'))
    self.assertFalse(graph.has_rule('m2:p'))
    self.assertFalse(graph.has_rule('x:x'))

  def testHasDependency(self):
    graph = RuleGraph(Project())
    with self.assertRaises(KeyError):
      graph.has_dependency('m1:a', 'm1:b')

    graph = RuleGraph(self.project)
    graph.add_rules_from_module(self.module_1)
    self.assertTrue(graph.has_dependency('m1:c', 'm1:c'))
    self.assertTrue(graph.has_dependency('m1:a3', 'm1:a3'))
    self.assertTrue(graph.has_dependency('m1:c', 'm1:b'))
    self.assertTrue(graph.has_dependency('m1:c', 'm1:a1'))
    self.assertTrue(graph.has_dependency('m1:b', 'm1:a1'))
    self.assertFalse(graph.has_dependency('m1:b', 'm1:c'))
    self.assertFalse(graph.has_dependency('m1:a1', 'm1:a2'))
    self.assertFalse(graph.has_dependency('m1:c', 'm1:a3'))
    with self.assertRaises(KeyError):
      graph.has_dependency('m1:c', 'm1:x')
    with self.assertRaises(KeyError):
      graph.has_dependency('m1:x', 'm1:c')
    with self.assertRaises(KeyError):
      graph.has_dependency('m1:x', 'm1:x')

  def testCalculateRuleSequence(self):
    graph = RuleGraph(self.project)

    with self.assertRaises(KeyError):
      graph.calculate_rule_sequence(':x')
    with self.assertRaises(KeyError):
      graph.calculate_rule_sequence([':x'])
    with self.assertRaises(KeyError):
      graph.calculate_rule_sequence(['m1:x'])

    seq = graph.calculate_rule_sequence('m1:a1')
    self.assertEqual(len(seq), 1)
    self.assertEqual(seq[0].name, 'a1')
    seq = graph.calculate_rule_sequence(['m1:a1'])
    self.assertEqual(len(seq), 1)
    self.assertEqual(seq[0].name, 'a1')

    seq = graph.calculate_rule_sequence(['m1:b'])
    self.assertEqual(len(seq), 3)
    self.assertTrue((seq[0].name in ['a1', 'a2']) or
                    (seq[1].name in ['a1', 'a2']))
    self.assertEqual(seq[2].name, 'b')

    seq = graph.calculate_rule_sequence(['m1:a1', 'm1:b'])
    self.assertEqual(len(seq), 3)
    self.assertTrue((seq[0].name in ['a1', 'a2']) or
                    (seq[1].name in ['a1', 'a2']))
    self.assertEqual(seq[2].name, 'b')

    seq = graph.calculate_rule_sequence(['m1:a1', 'm1:a3'])
    self.assertEqual(len(seq), 2)
    self.assertTrue((seq[0].name in ['a1', 'a3']) or
                    (seq[1].name in ['a1', 'a3']))

    module = Module('mx', rules=[Rule('a', deps=[':b'])])
    project = Project(modules=[module])
    graph = RuleGraph(project)
    with self.assertRaises(KeyError):
      graph.calculate_rule_sequence('mx:a')

  def testCrossModuleRules(self):
    graph = RuleGraph(self.project)

    seq = graph.calculate_rule_sequence(['m2:p'])
    self.assertEqual(len(seq), 5)
    self.assertTrue((seq[0].name in ['a1', 'a2']) or
                    (seq[1].name in ['a1', 'a2']))
    self.assertTrue(seq[4].path, 'm2:p')
    self.assertTrue(graph.has_dependency('m2:p', 'm1:a1'))


if __name__ == '__main__':
  unittest2.main()
