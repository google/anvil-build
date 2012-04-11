#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the rule module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

from anvil.rule import *
from anvil.test import FixtureTestCase


class RuleTest(unittest2.TestCase):
  """Behavioral tests of the Rule type."""

  def testRuleNames(self):
    with self.assertRaises(NameError):
      Rule(None)
    with self.assertRaises(NameError):
      Rule('')
    with self.assertRaises(NameError):
      Rule(' ')
    with self.assertRaises(NameError):
      Rule(' a')
    with self.assertRaises(NameError):
      Rule('a ')
    with self.assertRaises(NameError):
      Rule(' a ')
    with self.assertRaises(NameError):
      Rule('a\n')
    with self.assertRaises(NameError):
      Rule('a\t')
    with self.assertRaises(NameError):
      Rule('a b')
    with self.assertRaises(NameError):
      Rule(':a')
    rule = Rule('a')
    self.assertEqual(rule.name, 'a')
    self.assertEqual(rule.path, ':a')
    Rule('\u0CA_\u0CA')

  def testRuleSrcs(self):
    rule = Rule('r')
    self.assertEqual(len(rule.srcs), 0)

    srcs = ['a', 'b', ':c']
    rule = Rule('r', srcs=srcs)
    self.assertEqual(len(rule.srcs), 3)
    self.assertIsNot(rule.srcs, srcs)
    srcs[0] = 'x'
    self.assertEqual(rule.srcs[0], 'a')

    srcs = 'a'
    rule = Rule('r', srcs=srcs)
    self.assertEqual(len(rule.srcs), 1)
    self.assertEqual(rule.srcs[0], 'a')

    rule = Rule('r', srcs=None)
    rule = Rule('r', srcs='')
    self.assertEqual(len(rule.srcs), 0)
    with self.assertRaises(TypeError):
      Rule('r', srcs={})
    with self.assertRaises(TypeError):
      Rule('r', srcs=[None])
    with self.assertRaises(TypeError):
      Rule('r', srcs=[''])
    with self.assertRaises(TypeError):
      Rule('r', srcs=[{}])
    with self.assertRaises(NameError):
      Rule('r', srcs=' a')
    with self.assertRaises(NameError):
      Rule('r', srcs='a ')
    with self.assertRaises(NameError):
      Rule('r', srcs=' a ')

  def testRuleDeps(self):
    rule = Rule('r')
    self.assertEqual(len(rule.deps), 0)

    deps = [':a', ':b', ':c']
    rule = Rule('r', deps=deps)
    self.assertEqual(len(rule.deps), 3)
    self.assertIsNot(rule.deps, deps)
    deps[0] = 'x'
    self.assertEqual(rule.deps[0], ':a')

    deps = ':a'
    rule = Rule('r', deps=deps)
    self.assertEqual(len(rule.deps), 1)
    self.assertEqual(rule.deps[0], ':a')

    rule = Rule('r', deps=None)
    rule = Rule('r', deps='')
    self.assertEqual(len(rule.deps), 0)
    with self.assertRaises(TypeError):
      Rule('r', deps={})
    with self.assertRaises(TypeError):
      Rule('r', deps=[None])
    with self.assertRaises(TypeError):
      Rule('r', deps=[''])
    with self.assertRaises(TypeError):
      Rule('r', deps={})
    with self.assertRaises(NameError):
      Rule('r', deps=' a')
    with self.assertRaises(NameError):
      Rule('r', deps='a ')
    with self.assertRaises(NameError):
      Rule('r', deps=' a ')

  def testRuleDependentPaths(self):
    rule = Rule('r')
    self.assertEqual(rule.get_dependent_paths(), set([]))

    rule = Rule('r', srcs=[':a', 'a.txt'])
    self.assertEqual(rule.get_dependent_paths(), set([':a', 'a.txt']))

    rule = Rule('r', deps=[':a', 'm:b'])
    self.assertEqual(rule.get_dependent_paths(), set([':a', 'm:b']))

    rule = Rule('r', srcs=['a.txt'], deps=[':b'])
    self.assertEqual(rule.get_dependent_paths(), set(['a.txt', ':b']))

    rule = Rule('r', srcs=[':b'], deps=[':b'])
    self.assertEqual(rule.get_dependent_paths(), set([':b']))

    with self.assertRaises(NameError):
      Rule('r', deps=['a.txt'])

    class RuleWithAttrs(Rule):
      def __init__(self, name, extra_srcs=None, extra_deps=None,
                   *args, **kwargs):
        super(RuleWithAttrs, self).__init__(name, *args, **kwargs)
        self.extra_srcs = extra_srcs[:]
        self._append_dependent_paths(self.extra_srcs)
        self.extra_deps = extra_deps[:]
        self._append_dependent_paths(self.extra_deps, require_semicolon=True)

    rule = RuleWithAttrs('r', srcs=['a.txt'], deps=[':b'],
                         extra_srcs=['c.txt'], extra_deps=[':d'])
    self.assertEqual(rule.get_dependent_paths(), set([
        'a.txt', ':b', 'c.txt', ':d']))

  def testRuleCacheKey(self):
    rule1 = Rule('r1')
    rule1_key = rule1.compute_cache_key()
    self.assertIsNotNone(rule1_key)
    self.assertGreater(len(rule1_key), 0)
    self.assertEqual(rule1_key, rule1.compute_cache_key())
    rule1.srcs.append('a')
    self.assertNotEqual(rule1_key, rule1.compute_cache_key())

    rule1 = Rule('r1')
    rule2 = Rule('r1')
    self.assertEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1')
    rule2 = Rule('r2')
    self.assertNotEqual(rule1.compute_cache_key(), rule2.compute_cache_key())

    rule1 = Rule('r1', srcs='a')
    rule2 = Rule('r1', srcs='a')
    self.assertEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1', srcs='a')
    rule2 = Rule('r1', srcs='b')
    self.assertNotEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1', deps=':a')
    rule2 = Rule('r1', deps=':a')
    self.assertEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1', deps=':a')
    rule2 = Rule('r1', deps=':b')
    self.assertNotEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1', srcs='a', deps=':a')
    rule2 = Rule('r1', srcs='a', deps=':a')
    self.assertEqual(rule1.compute_cache_key(), rule2.compute_cache_key())
    rule1 = Rule('r1', srcs='a', deps=':a')
    rule2 = Rule('r1', srcs='b', deps=':b')
    self.assertNotEqual(rule1.compute_cache_key(), rule2.compute_cache_key())

  def testRuleFilter(self):
    rule = Rule('a')
    self.assertIsNone(rule.src_filter)
    rule = Rule('a', src_filter='')
    self.assertIsNone(rule.src_filter)
    rule = Rule('a', src_filter='*.js')
    self.assertEqual(rule.src_filter, '*.js')


class RuleNamespaceTest(FixtureTestCase):
  """Behavioral tests of the Rule type."""
  fixture = 'rules'

  def testManual(self):
    ns = RuleNamespace()
    self.assertEqual(len(ns.rule_types), 0)

    class MockRule1(Rule):
      pass
    ns.add_rule_type('mock_rule_1', MockRule1)
    self.assertEqual(len(ns.rule_types), 1)

    with self.assertRaises(KeyError):
      ns.add_rule_type('mock_rule_1', MockRule1)

  def testDiscovery(self):
    ns = RuleNamespace()
    ns.discover()
    self.assertTrue(ns.rule_types.has_key('file_set'))

    rule_path = self.root_path
    ns = RuleNamespace()
    ns.discover(rule_path)
    self.assertEqual(len(ns.rule_types), 3)
    self.assertFalse(ns.rule_types.has_key('file_set'))
    self.assertTrue(ns.rule_types.has_key('rule_a'))
    self.assertTrue(ns.rule_types.has_key('rule_b'))
    self.assertTrue(ns.rule_types.has_key('rule_c'))
    self.assertFalse(ns.rule_types.has_key('rule_x'))

    rule_path = os.path.join(self.root_path, 'dupe.py')
    ns = RuleNamespace()
    with self.assertRaises(KeyError):
      ns.discover(rule_path)
    self.assertEqual(len(ns.rule_types), 0)

    rule_path = os.path.join(self.root_path, 'more', 'more_rules.py')
    ns = RuleNamespace()
    ns.discover(rule_path)
    self.assertEqual(len(ns.rule_types), 1)
    self.assertTrue(ns.rule_types.has_key('rule_c'))


if __name__ == '__main__':
  unittest2.main()
