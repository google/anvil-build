# Copyright 2012 Google Inc. All Rights Reserved.

"""Builds a set of target rules.

Examples:
# Build the given rules
anvil build :some_rule some/path:another_rule
# Force a full rebuild (essentially a 'anvil clean')
anvil build --rebuild :some_rule
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import anvil.commands.util as commandutil
from anvil.manage import ManageCommand


class BuildCommand(ManageCommand):
  def __init__(self):
    super(BuildCommand, self).__init__(
        name='build',
        help_short='Builds target rules.',
        help_long=__doc__)
    self._add_common_build_hints()
    self.completion_hints.extend([
        '--rebuild',
        ])

  def create_argument_parser(self):
    parser = super(BuildCommand, self).create_argument_parser()

    # Add all common args
    self._add_common_build_arguments(parser, targets=True)

    # 'build' specific
    parser.add_argument('--rebuild',
                        dest='rebuild',
                        action='store_true',
                        default=False,
                        help=('Cleans all output and caches before building.'))

    return parser

  def execute(self, args, cwd):
    # Handle --rebuild
    if args.rebuild:
      if not commandutil.clean_output(cwd):
        return False

    (result, all_target_outputs) = commandutil.run_build(cwd, args)

    print('result %s, %s outputs' % (result, len(all_target_outputs)))
    #print all_target_outputs

    return 0 if result else 1
