# Copyright 2012 Google Inc. All Rights Reserved.

"""Builds a set of target rules.

Examples:
# Build the given rules
manage.py build :some_rule some/path:another_rule
# Force a full rebuild (essentially a 'manage.py clean')
manage.py build --rebuild :some_rule
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import anvil.commands.util as commandutil
from anvil.manage import manage_command


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('manage.py build', __doc__)

  # Add all common args
  commandutil.add_common_build_args(parser, targets=True)

  # 'build' specific
  parser.add_argument('--rebuild',
                      dest='rebuild',
                      action='store_true',
                      default=False,
                      help=('Cleans all output and caches before building.'))

  return parser


@manage_command('build', 'Builds target rules.')
def build(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  # Handle --rebuild
  if parsed_args.rebuild:
    if not commandutil.clean_output(cwd):
      return False

  (result, all_target_outputs) = commandutil.run_build(cwd, parsed_args)

  print all_target_outputs

  return result
