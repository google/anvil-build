#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the util module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import sys
import unittest2

from anvil import util


class IsRulePathTest(unittest2.TestCase):
  """Behavioral tests of the is_rule_path method."""

  def testEmpty(self):
    self.assertFalse(util.is_rule_path(None))
    self.assertFalse(util.is_rule_path(''))

  def testTypes(self):
    self.assertFalse(util.is_rule_path(4))
    self.assertFalse(util.is_rule_path(['a']))
    self.assertFalse(util.is_rule_path({'a': 1}))

  def testNames(self):
    self.assertTrue(util.is_rule_path(':a'))
    self.assertTrue(util.is_rule_path(':ab'))
    self.assertTrue(util.is_rule_path('xx:ab'))
    self.assertTrue(util.is_rule_path('/a/b:ab'))

    self.assertFalse(util.is_rule_path('a'))
    self.assertFalse(util.is_rule_path('/a/b.c'))
    self.assertFalse(util.is_rule_path('a b c'))


class ValidateNamesTest(unittest2.TestCase):
  """Behavioral tests of the validate_names method."""

  def testEmpty(self):
    util.validate_names(None)
    util.validate_names([])

  def testNames(self):
    util.validate_names(['a'])
    util.validate_names([':a'])
    util.validate_names(['xx:a'])
    util.validate_names(['/a/b:a'])
    util.validate_names(['/a/b.c:a'])
    util.validate_names(['/a/b.c/:a'])
    util.validate_names(['a', ':b'])
    with self.assertRaises(TypeError):
      util.validate_names([None])
    with self.assertRaises(TypeError):
      util.validate_names([''])
    with self.assertRaises(TypeError):
      util.validate_names([{}])
    with self.assertRaises(NameError):
      util.validate_names([' a'])
    with self.assertRaises(NameError):
      util.validate_names(['a '])
    with self.assertRaises(NameError):
      util.validate_names([' a '])
    with self.assertRaises(NameError):
      util.validate_names(['a', ' b'])

  def testRequireSemicolon(self):
    util.validate_names([':a'], require_semicolon=True)
    util.validate_names([':a', ':b'], require_semicolon=True)
    util.validate_names(['C:/a/:b'], require_semicolon=True)
    util.validate_names(['C:\\a\\:b'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names(['a'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names([':a', 'b'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names([':/a'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names([':\\a'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names(['C:\\a'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names(['C:\\a:\\b'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names([':a/b'], require_semicolon=True)
    with self.assertRaises(NameError):
      util.validate_names(['a:b/a'], require_semicolon=True)


class UnderscoreToPascalCaseTest(unittest2.TestCase):
  """Behavioral tests of the underscore_to_pascalcase method."""

  def testEmpty(self):
    self.assertEqual(
        util.underscore_to_pascalcase(None),
        None)
    self.assertEqual(
        util.underscore_to_pascalcase(''),
        '')

  def testUnderscores(self):
    self.assertEqual(
        util.underscore_to_pascalcase('ab'),
        'Ab')
    self.assertEqual(
        util.underscore_to_pascalcase('aB'),
        'Ab')
    self.assertEqual(
        util.underscore_to_pascalcase('AB'),
        'Ab')
    self.assertEqual(
        util.underscore_to_pascalcase('a_b'),
        'AB')
    self.assertEqual(
        util.underscore_to_pascalcase('A_b'),
        'AB')
    self.assertEqual(
        util.underscore_to_pascalcase('aa_bb'),
        'AaBb')
    self.assertEqual(
        util.underscore_to_pascalcase('aa1_bb2'),
        'Aa1Bb2')
    self.assertEqual(
        util.underscore_to_pascalcase('1aa_2bb'),
        '1aa2bb')

  def testWhitespace(self):
    self.assertEqual(
        util.underscore_to_pascalcase(' '),
        ' ')
    self.assertEqual(
        util.underscore_to_pascalcase(' a'),
        ' a')
    self.assertEqual(
        util.underscore_to_pascalcase('a '),
        'A ')
    self.assertEqual(
        util.underscore_to_pascalcase(' a '),
        ' a ')
    self.assertEqual(
        util.underscore_to_pascalcase('a b'),
        'A b')
    self.assertEqual(
        util.underscore_to_pascalcase('a  b'),
        'A  b')

class WhichTest(unittest2.TestCase):
  """Behavioral tests of the which method."""

  @unittest2.skipUnless(sys.platform.startswith('win'), 'platform')
  def testWindows(self):
    notepad_path = 'C:\\Windows\\System32\\notepad.exe'
    self.assertEqual(util.which(notepad_path), notepad_path)
    self.assertIsNone(util.which('xxx'))
    self.assertIsNotNone(util.which('notepad.exe'))

  @unittest2.skipIf(sys.platform.startswith('win'), 'platform')
  def testUnix(self):
    self.assertEqual(util.which('/bin/sh'), '/bin/sh')
    self.assertIsNone(util.which('xxx'))
    self.assertIsNotNone(util.which('cat'))


if __name__ == '__main__':
  unittest2.main()
