#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the manage module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import types
import unittest2

import manage
import test
from manage import *
from test import AsyncTestCase, FixtureTestCase


class ManageTest(FixtureTestCase):
  """Behavioral tests for the management wrapper."""
  fixture = 'manage'

  def testDecorator(self):
    @manage_command('command_1')
    def command_1(args, cwd):
      return 0
    self.assertEqual(command_1.command_name, 'command_1')

  def testDiscovery(self):
    # Check built-in
    commands = manage.discover_commands()
    self.assertTrue(commands.has_key('build'))
    self.assertIsInstance(commands['build'], types.FunctionType)

    # Check custom
    commands = manage.discover_commands(
        os.path.join(self.root_path, 'commands'))
    self.assertTrue(commands.has_key('test_command'))
    self.assertIsInstance(commands['test_command'], types.FunctionType)
    self.assertEqual(commands['test_command']([], ''), 123)

    # Duplicate command names/etc
    with self.assertRaises(KeyError):
      manage.discover_commands(os.path.join(self.root_path, 'bad_commands'))

  def testUsage(self):
    commands = manage.discover_commands()
    self.assertNotEqual(len(manage.usage(commands)), 0)

  def testMain(self):
    with self.assertRaises(ValueError):
      manage.run_command()
    with self.assertRaises(ValueError):
      manage.run_command(['xxx'])

    def some_command(args, cwd):
      self.assertEqual(len(args), 0)
      self.assertNotEqual(len(cwd), 0)
      return 123
    self.assertEqual(manage.run_command(
        ['some_command'], commands={'some_command': some_command}), 123)


if __name__ == '__main__':
  unittest2.main()
