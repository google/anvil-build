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
from anvil.manage import manage_command


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('anvil test', __doc__)

  # Add all common args
  commandutil.add_common_build_args(parser, targets=True)

  # 'test' specific

  return parser


@manage_command('test', 'Builds and runs test rules.')
def test(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  (result, all_target_outputs) = commandutil.run_build(cwd, parsed_args)

  print all_target_outputs

  return result
