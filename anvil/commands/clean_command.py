# Copyright 2012 Google Inc. All Rights Reserved.

"""Cleans all build-* paths and caches.
Attempts to delete all paths the build system creates.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import shutil
import sys

import anvil.commands.util as commandutil
from anvil.manage import manage_command


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('anvil clean', __doc__)

  # 'clean' specific

  return parser


@manage_command('clean', 'Cleans outputs and caches.')
def clean(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  return commandutil.clean_output(cwd)
