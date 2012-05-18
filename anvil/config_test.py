#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the config module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

import anvil.config
from anvil.test import FixtureTestCase


class ConfigTest(FixtureTestCase):
  """Behavioral tests for config loading."""
  fixture = 'config'

  def testNone(self):
    config = anvil.config.load(os.path.dirname(self.root_path))
    self.assertIsNotNone(config)
    self.assertFalse(config.has_option('a', 'opt'))

  def testLoading(self):
    config = anvil.config.load(self.root_path)
    self.assertIsNotNone(config)
    self.assertTrue(config.has_option('a', 'opt'))
    self.assertEqual(config.get('a', 'opt'), 'hello')

  def testDeep(self):
    config = anvil.config.load(os.path.join(self.root_path, 'deep'))
    self.assertIsNotNone(config)
    self.assertTrue(config.has_option('a', 'opt'))
    self.assertEqual(config.get('a', 'opt'), 'world')
    self.assertTrue(config.has_option('b', 'opt'))
    self.assertEqual(config.get('b', 'opt'), 'another')

    config = anvil.config.load(os.path.join(self.root_path, 'deep', 'none'))
    self.assertIsNotNone(config)
    self.assertTrue(config.has_option('a', 'opt'))
    self.assertEqual(config.get('a', 'opt'), 'world')
    self.assertTrue(config.has_option('b', 'opt'))
    self.assertEqual(config.get('b', 'opt'), 'another')


if __name__ == '__main__':
  unittest2.main()
