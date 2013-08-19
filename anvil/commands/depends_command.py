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
anvil depends :some_rule
# Install/update all dependencies for rule :some_rule
anvil depends --install :some_rule
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import argparse
import os
import sys

from anvil.depends import DependencyManager
from anvil.manage import ManageCommand


class DependsCommand(ManageCommand):
  def __init__(self):
    super(DependsCommand, self).__init__(
        name='depends',
        help_short='Manages external rule type dependencies.',
        help_long=__doc__)
    self.completion_hints.extend([
        '-i', '--install',
        '--stop_on_error',
        ])

  def create_argument_parser(self):
    parser = super(DependsCommand, self).create_argument_parser()

    # 'depends' specific
    parser.add_argument('-i', '--install',
                        dest='install',
                        action='store_true',
                        default=False,
                        help=('Install any missing dependencies. Must be run '
                              'as root.'))
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

  def execute(self, args, cwd):
    dep_manager = DependencyManager(cwd=cwd)
    dependencies = dep_manager.scan_dependencies(args.targets)

    if not len(dependencies):
      print('No requirements found')
      return True

    if not args.install:
      # TODO(benvanik): prettier output
      for dependency in dependencies:
        print(dependency)
      return True

    # TODO(benvanik): check if running as root
    running_as_root = False
    if args.install and not running_as_root:
      print('Not running as root - run again with sudo')
      return False

    result = dep_manager.install_all(dependencies)
    return 0 if result else 1
