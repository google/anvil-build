#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the module module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import glob2
import os
import unittest2

from anvil.module import *
from anvil.rule import *
from anvil.test import FixtureTestCase


class ModuleTest(unittest2.TestCase):
  """Behavioral tests of Module rule handling."""

  def testEmptyModule(self):
    module = Module('m')
    self.assertIsNone(module.get_rule(':a'))
    self.assertEqual(len(module.rule_list()), 0)
    self.assertEqual(len(list(module.rule_iter())), 0)

  def testModulePath(self):
    module = Module('a')
    self.assertEqual(module.path, 'a')

  def testModuleRuleInit(self):
    rule_a = Rule('a')
    rule_b = Rule('b')
    rule_list = [rule_a, rule_b]
    module = Module('m', rules=rule_list)
    self.assertIsNot(module.rule_list(), rule_list)
    self.assertEqual(len(module.rule_list()), len(rule_list))
    self.assertIs(module.get_rule(':a'), rule_a)
    self.assertIs(module.get_rule(':b'), rule_b)

  def testAddRule(self):
    rule_a = Rule('a')
    rule_b = Rule('b')

    module = Module('m')
    self.assertIsNone(module.get_rule(':a'))

    module.add_rule(rule_a)
    self.assertIs(module.get_rule('a'), rule_a)
    self.assertIs(module.get_rule(':a'), rule_a)
    self.assertEqual(len(module.rule_list()), 1)
    self.assertEqual(len(list(module.rule_iter())), 1)
    self.assertIs(module.rule_list()[0], rule_a)
    self.assertEqual(list(module.rule_iter())[0], rule_a)
    self.assertIsNone(module.get_rule(':b'))

    module.add_rule(rule_b)
    self.assertIs(module.get_rule(':b'), rule_b)
    self.assertEqual(len(module.rule_list()), 2)
    self.assertEqual(len(list(module.rule_iter())), 2)

    with self.assertRaises(KeyError):
      module.add_rule(rule_b)
    self.assertEqual(len(module.rule_list()), 2)

  def testAddRules(self):
    rule_a = Rule('a')
    rule_b = Rule('b')
    rule_list = [rule_a, rule_b]

    module = Module('m')
    self.assertIsNone(module.get_rule('a'))
    self.assertIsNone(module.get_rule(':a'))
    self.assertIsNone(module.get_rule('b'))
    self.assertIsNone(module.get_rule(':b'))
    self.assertEqual(len(module.rule_list()), 0)

    module.add_rules(rule_list)
    self.assertEqual(len(module.rule_list()), 2)
    self.assertEqual(len(list(module.rule_iter())), 2)
    self.assertIsNot(module.rule_list(), rule_list)
    self.assertIs(module.get_rule(':a'), rule_a)
    self.assertIs(module.get_rule(':b'), rule_b)

    with self.assertRaises(KeyError):
      module.add_rule(rule_b)
    self.assertEqual(len(module.rule_list()), 2)
    with self.assertRaises(KeyError):
      module.add_rules([rule_b])
    self.assertEqual(len(module.rule_list()), 2)
    with self.assertRaises(KeyError):
      module.add_rules(rule_list)
    self.assertEqual(len(module.rule_list()), 2)

  def testGetRule(self):
    rule = Rule('a')
    module = Module('m')
    module.add_rule(rule)

    self.assertIs(module.get_rule('a'), rule)
    self.assertIs(module.get_rule(':a'), rule)

    self.assertIsNone(module.get_rule(':x'))

    with self.assertRaises(NameError):
      module.get_rule('')
    with self.assertRaises(NameError):
      module.get_rule(':')

  def testRuleParentModule(self):
    rule_a = Rule('a')
    module = Module('m')

    self.assertIsNone(rule_a.parent_module)
    self.assertEqual(rule_a.path, ':a')

    module.add_rule(rule_a)

    self.assertIs(rule_a.parent_module, module)
    self.assertEqual(rule_a.path, 'm:a')

    with self.assertRaises(ValueError):
      rule_a.set_parent_module(module)


class ModuleLoaderTest(FixtureTestCase):
  """Behavioral tests for ModuleLoader."""
  fixture = 'simple'

  def testModes(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')

    loader = ModuleLoader(module_path)
    self.assertEqual(len(loader.modes), 0)
    loader = ModuleLoader(module_path, modes=None)
    self.assertEqual(len(loader.modes), 0)
    loader = ModuleLoader(module_path, modes=[])
    self.assertEqual(len(loader.modes), 0)
    loader = ModuleLoader(module_path, modes=['A'])
    self.assertEqual(len(loader.modes), 1)
    modes = ['A', 'B']
    loader = ModuleLoader(module_path, modes=modes)
    self.assertIsNot(loader.modes, modes)
    self.assertEqual(len(loader.modes), 2)

    with self.assertRaises(KeyError):
      ModuleLoader(module_path, modes=['A', 'A'])

  def testLoad(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')
    loader = ModuleLoader(module_path)
    loader.load()

    loader = ModuleLoader(module_path + '.not-real')
    with self.assertRaises(IOError):
      loader.load()

    loader = ModuleLoader(module_path)
    loader.load(source_string='x = 5')
    with self.assertRaises(Exception):
      loader.load(source_string='y = 5')

    loader = ModuleLoader(module_path)
    with self.assertRaises(SyntaxError):
      loader.load(source_string='x/')
    with self.assertRaises(Exception):
      loader.load(source_string='y = 5')

  def testExecute(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')

    loader = ModuleLoader(module_path)
    loader.load(source_string='asdf()')
    with self.assertRaises(NameError):
      loader.execute()

    loader = ModuleLoader(module_path)
    loader.load(source_string='')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 0)

    loader = ModuleLoader(module_path)
    loader.load(source_string='x = 5')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 0)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a")\nfile_set("b")')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 2)
    self.assertIsNotNone(module.get_rule(':a'))
    self.assertIsNotNone(module.get_rule(':b'))
    self.assertEqual(module.get_rule(':a').name, 'a')
    self.assertEqual(module.get_rule(':b').name, 'b')

  def testBuiltins(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')

    loader = ModuleLoader(module_path, modes=['A'])
    loader.load(source_string=(
        'file_set("a", srcs=select_any({"A": "sa"}, "sx"))\n'
        'file_set("b", srcs=select_any({"B": "sb"}, "sx"))\n'
        'file_set("c", srcs=select_one([("A", "sa")], "sx"))\n'
        'file_set("d", srcs=select_many({"B": "sb"}, "sx"))\n'))
    module = loader.execute()
    self.assertEqual(module.get_rule(':a').srcs[0], 'sa')
    self.assertEqual(module.get_rule(':b').srcs[0], 'sx')
    self.assertEqual(module.get_rule(':c').srcs[0], 'sa')
    self.assertEqual(module.get_rule(':d').srcs[0], 'sx')

  def testCustomRules(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')

    class MockRule1(Rule):
      pass
    rule_namespace = RuleNamespace()
    rule_namespace.add_rule_type('mock_rule_1', MockRule1)
    loader = ModuleLoader(module_path, rule_namespace=rule_namespace)
    loader.load(source_string='mock_rule_1("a")')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    self.assertEqual(module.get_rule(':a').name, 'a')

  def testGlob(self):
    module_path = os.path.join(self.temp_path, 'simple', 'BUILD')

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob(""))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 0)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob("*.txt"))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 3)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob("**/*.txt"))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 5)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob("a.txt"))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 1)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob("x.txt"))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 0)

    loader = ModuleLoader(module_path)
    loader.load(source_string='file_set("a", srcs=glob("*.notpresent"))')
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))
    rule = module.get_rule(':a')
    self.assertEqual(len(rule.srcs), 0)


class ModuleLoaderIncludeTest(FixtureTestCase):
  """Behavioral tests for ModuleLoader include functionality."""
  fixture = 'custom_rules'

  def testIncludeRulesSingle(self):
    module_path = os.path.join(self.temp_path, 'custom_rules', 'BUILD')

    rule_namespace = RuleNamespace()
    loader = ModuleLoader(module_path, rule_namespace=rule_namespace)
    loader.load(source_string=(
        'include_rules("rules/some_rules.py")\n'
        'some_rule(name="a")\n'))
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 1)
    self.assertIsNotNone(module.get_rule(':a'))

  def testIncludeRulesGlob(self):
    module_path = os.path.join(self.temp_path, 'custom_rules', 'BUILD')

    rule_namespace = RuleNamespace()
    loader = ModuleLoader(module_path, rule_namespace=rule_namespace)
    loader.load(source_string=(
        'include_rules(glob("rules/**/*_rules.py"))\n'
        'some_rule(name="a")\n'
        'other_rule(name="b")\n'))
    module = loader.execute()
    self.assertEqual(len(module.rule_list()), 2)
    self.assertIsNotNone(module.get_rule(':a'))
    self.assertIsNotNone(module.get_rule(':b'))

  # def testIncludeRulesRef(self):
  #   module_path = os.path.join(self.temp_path, 'custom_rules', 'BUILD')

  #   rule_namespace = RuleNamespace()
  #   loader = ModuleLoader(module_path, rule_namespace=rule_namespace)
  #   loader.load(source_string=(
  #       'file_set(name="rules", srcs=glob("rules/**/*_rules.py"))\n'
  #       'include_rules(":rules")\n'
  #       'some_rule(name="a")\n'
  #       'other_rule(name="b")\n'))
  #   module = loader.execute()
  #   self.assertEqual(len(module.rule_list()), 2)
  #   self.assertIsNotNone(module.get_rule(':a'))
  #   self.assertIsNotNone(module.get_rule(':b'))

  # def testIncludeRulesRefOther(self):
  #   module_path = os.path.join(self.temp_path, 'custom_rules', 'BUILD')

  #   rule_namespace = RuleNamespace()
  #   loader = ModuleLoader(module_path, rule_namespace=rule_namespace)
  #   loader.load(source_string=(
  #       'include_rules("rules:all_rules")\n'
  #       'some_rule(name="a")\n'
  #       'other_rule(name="b")\n'))
  #   module = loader.execute()
  #   self.assertEqual(len(module.rule_list()), 2)
  #   self.assertIsNotNone(module.get_rule(':a'))
  #   self.assertIsNotNone(module.get_rule(':b'))


class ModuleLoaderSelectionTest(unittest2.TestCase):
  """Behavioral tests for ModuleLoader selection utilities."""

  def testSelectOne(self):
    loader = ModuleLoader('some/path')
    self.assertEqual(loader.select_one([
        ], default_value=100), 100)
    self.assertEqual(loader.select_one([
        ('A', 1),
        ('B', 2),
        ], default_value=100), 100)

    loader = ModuleLoader('some/path', modes=['A', 'B', 'C'])
    self.assertEqual(loader.select_one([
        ('X', 99),
        ], default_value=100), 100)
    self.assertEqual(loader.select_one([
        ('A', 1),
        ], default_value=100), 1)
    self.assertEqual(loader.select_one([
        ('A', 1),
        ('B', 2),
        ], default_value=100), 2)
    self.assertEqual(loader.select_one([
        ('B', 2),
        ('A', 1),
        ], default_value=100), 1)

  def testSelectAny(self):
    loader = ModuleLoader('some/path')
    self.assertEqual(loader.select_any({
        }, default_value=100), 100)
    self.assertIsNone(loader.select_any({
        'A': 1,
        'B': 2,
        }, default_value=None))
    self.assertEqual(loader.select_any({
        'A': 1,
        'B': 2,
        }, default_value=100), 100)

    loader = ModuleLoader('some/path', modes=['A', 'B', 'C'])
    self.assertEqual(loader.select_any({
        }, default_value=100), 100)
    self.assertEqual(loader.select_any({
        'X': 99,
        }, default_value=100), 100)
    self.assertEqual(loader.select_any({
        'X': 99,
        'A': 1,
        }, default_value=100), 1)
    self.assertEqual(loader.select_any({
        'X': 99,
        'B': 2,
        }, default_value=100), 2)

    with self.assertRaises(KeyError):
      loader.select_any({
          'A': 1,
          'B': 2,
          }, default_value=100)

  def testSelectMany(self):
    loader = ModuleLoader('some/path')
    self.assertIsNone(loader.select_many({}, default_value=None))
    self.assertEqual(loader.select_many({}, default_value=[]), [])
    self.assertEqual(loader.select_many({}, default_value=[1]), [1])
    self.assertEqual(loader.select_many({}, default_value={}), {})
    self.assertEqual(loader.select_many({}, default_value={'a': 1}), {'a': 1})
    self.assertEqual(loader.select_many({}, default_value=1), [1])
    self.assertEqual(loader.select_many({}, default_value='a'), ['a'])
    self.assertEqual(loader.select_many({
        'A': 1,
        }, default_value=100), [100])
    self.assertEqual(loader.select_many({
        'A': [1, 2, 3],
        }, default_value=[100, 101, 102]), [100, 101, 102])
    self.assertEqual(loader.select_many({
        'A': {'a': 1},
        }, default_value={'d': 100}), {'d': 100})

    loader = ModuleLoader('some/path', modes=['A', 'B', 'C'])
    self.assertEqual(loader.select_many({}, default_value=[]), [])
    self.assertEqual(loader.select_many({
        'X': 1,
        }, default_value=100), [100])
    self.assertEqual(loader.select_many({
        'A': 1,
        }, default_value=100), [1])
    self.assertEqual(loader.select_many({
        'A': 1,
        'B': 2,
        }, default_value=100), [1, 2])
    self.assertEqual(loader.select_many({
        'A': [1, 2, 3],
        }, default_value=[100]), [1, 2, 3])
    self.assertEqual(loader.select_many({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        }, default_value=[100]), [1, 2, 3, 4, 5, 6])
    self.assertEqual(loader.select_many({
        'A': {'a': 1},
        }, default_value={'d': 100}), {'a': 1})
    self.assertEqual(loader.select_many({
        'A': {'a': 1},
        'B': {'b': 2},
        }, default_value={'d': 100}), {'a': 1, 'b': 2})

    with self.assertRaises(TypeError):
      loader.select_many({
          'A': 1,
          }, default_value=[100])
    with self.assertRaises(TypeError):
      loader.select_many({
          'A': 1,
          }, default_value={'d': 100})
    with self.assertRaises(TypeError):
      loader.select_many({
          'A': [1],
          }, default_value=100)
    with self.assertRaises(TypeError):
      loader.select_many({
          'A': [1],
          }, default_value={'d': 100})
    with self.assertRaises(TypeError):
      loader.select_many({
          'A': {'a': 1},
          }, default_value=100)
    with self.assertRaises(TypeError):
      loader.select_many({
          'A': {'a': 1},
          }, default_value=[100])


if __name__ == '__main__':
  unittest2.main()
