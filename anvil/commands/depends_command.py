# Copyright 2012 Google Inc. All Rights Reserved.

"""Scans all reachable rules for dependencies and installs them.
Given a set of target rules, all reachable rules will be scanned for
dependencies that they require to function (such as external Python libraries,
system tools/libraries/etc).

If the --install option is passed to the command it will attempt to install or
update all of the discovered dependencies. The command must be run as root
(via sudo) in order for this to work. For dependencies that install locally
(such as Node.js modules) they will be placed in the current working directory.

TODO(benvanik): it'd be nice to support * syntax or some way to say 'everything'

Example:
# Check dependencies and print results for rule :some_rule
manage.py depends :some_rule
# Install/update all dependencies for rule :some_rule
manage.py depends --install :some_rule
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import argparse
import os
import sys

import anvil.commands.util as commandutil
from anvil.depends import DependencyManager
from anvil.manage import manage_command


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('manage.py depends', __doc__)

  # Add all common args

  # 'depends' specific
  parser.add_argument('-i', '--install',
                      dest='install',
                      action='store_true',
                      default=False,
                      help=('Install any missing dependencies. Must be run as '
                            'root.'))
  parser.add_argument('--stop_on_error',
                      dest='stop_on_error',
                      action='store_true',
                      default=False,
                      help=('Stop installing when an error is encountered.'))
  parser.add_argument('targets',
                        nargs='+',
                        metavar='target',
                        help='Target build rule (such as :a or foo/bar:a)')

  return parser


@manage_command('depends', 'Manages external rule dependencies.')
def depends(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  dep_manager = DependencyManager(cwd=cwd)
  dependencies = dep_manager.scan_dependencies(parsed_args.targets)

  if not len(requirements):
    print 'No requirements found'
    return True

  if not parsed_args.install:
    # TODO(benvanik): prettier output
    for dependency in dependencies:
      print dependency
    return True

  # TODO(benvanik): check if running as root
  running_as_root = False
  if parsed_args.install and not running_as_root:
    print 'Not running as root - run again with sudo'
    return False

  return dep_manager.install_all(dependencies)
