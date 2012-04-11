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

  def testDiscovery(self):
    # Check built-in
    commands = manage.discover_commands()
    self.assertTrue(commands.has_key('build'))
    self.assertIsInstance(commands['build'], ManageCommand)

    # Check custom
    commands = manage.discover_commands(
        os.path.join(self.root_path, 'commands'))
    self.assertTrue(commands.has_key('test_command'))
    test_command = commands['test_command']
    self.assertIsInstance(test_command, ManageCommand)
    args = test_command.create_argument_parser()
    parsed_args = args.parse_args([])
    cwd = os.getcwd()
    self.assertEqual(commands['test_command'].execute(parsed_args, cwd), 123)

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

    class SomeCommand(ManageCommand):
      def __init__(self):
        super(SomeCommand, self).__init__(name='some_command')
      def execute(self, args, cwd):
        return 123
    self.assertEqual(manage.run_command(
        ['some_command'], commands={'some_command': SomeCommand()}), 123)


if __name__ == '__main__':
  unittest2.main()
