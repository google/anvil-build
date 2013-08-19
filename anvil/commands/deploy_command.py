# Copyright 2012 Google Inc. All Rights Reserved.

"""Runs a build and copies all output results of the specified rules to a path.
All of the output files of the specified rules will be copied to the target
output path. The directory structure will be exactly that of under the
various build-*/ folders but collapsed into one.

A typical deploy rule will bring together many result srcs, for example
converted audio files or compiled code, for a specific configuration.
One could have many such rules to target different configurations, such as
unoptimized/uncompiled vs. optimized/packed.

Examples:
# Copy all output files of :release_all to /some/bin/, merging the output
anvil deploy --output=/some/bin/ :release_all
# Clean (aka delete) /some/bin/ before doing the copy
anvil deploy --clean --output=/some/bin/ :release_all
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import shutil
import sys

import anvil.commands.util as commandutil
from anvil.manage import ManageCommand


class DeployCommand(ManageCommand):
  def __init__(self):
    super(DeployCommand, self).__init__(
        name='deploy',
        help_short='Builds and copies output to a target path.',
        help_long=__doc__)
    self._add_common_build_hints()
    self.completion_hints.extend([
        '-o', '--output',
        '-c', '--clean',
        ])

  def create_argument_parser(self):
    parser = super(DeployCommand, self).create_argument_parser()

    # Add all common args
    self._add_common_build_arguments(parser, targets=True)

    # 'deploy' specific
    parser.add_argument('-o', '--output',
                        dest='output',
                        required=True,
                        help=('Output path to place all results. Will be '
                              'created if it does not exist.'))
    parser.add_argument('-c', '--clean',
                        dest='clean',
                        action='store_true',
                        help=('Whether to remove all output files before '
                              'deploying.'))

    return parser

  def execute(self, args, cwd):
    # Build everything first
    (result, all_target_outputs) = commandutil.run_build(cwd, args)
    if not result:
      # Failed - don't copy anything
      return False

    # Delete output, if desired
    if args.clean:
      try:
        shutil.rmtree(args.output)
      except:
        pass

    # Ensure output exists
    if not os.path.isdir(args.output):
      os.makedirs(args.output)

    # Sort all outputs by path, as it makes things prettier
    all_target_outputs = list(all_target_outputs)
    all_target_outputs.sort()

    # Copy results
    print('')
    print('Copying results to %s:' % (args.output))
    for target_output in all_target_outputs:
      # Get path relative to root
      # This will contain the build-out/ etc
      rel_path = os.path.relpath(target_output, cwd)

      # Strip the build-*/
      # TODO(benvanik): a more reliable strip
      rel_path_parts = rel_path.split(os.sep)
      if rel_path_parts[0].startswith('build-'):
        rel_path = os.path.join(*(rel_path_parts[1:]))

      # Make output path
      deploy_path = os.path.normpath(os.path.join(args.output, rel_path))

      # Ensure directory exists
      # TODO(benvanik): cache whether we have checked yet to reduce OS cost
      deploy_dir = os.path.dirname(deploy_path)
      if not os.path.isdir(deploy_dir):
        os.makedirs(deploy_dir)

      # Copy!
      print('%s -> %s' % (rel_path, deploy_path))
      shutil.copy(target_output, deploy_path)

    return 0 if result else 1
