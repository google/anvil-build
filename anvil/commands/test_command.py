# Copyright 2012 Google Inc. All Rights Reserved.

"""Builds and executes a set of test rules.
TODO: need some custom rules (test_js or something?) that provide parameters
      to some test framework (BusterJS?)

Example:
anvil test :test_rule ...
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import sys

import anvil.commands.util as commandutil
from anvil.manage import ManageCommand


class TestCommand(ManageCommand):
  def __init__(self):
    super(TestCommand, self).__init__(
        name='test',
        help_short='Builds and runs test rules.',
        help_long=__doc__)
    self._add_common_build_hints()

  def create_argument_parser(self):
    parser = super(TestCommand, self).create_argument_parser()

    # Add all common args
    self._add_common_build_arguments(parser, targets=True)

    return parser

  def execute(self, args, cwd):
    (result, all_target_outputs) = commandutil.run_build(cwd, args)

    print(all_target_outputs)

    return 0 if result else 1
