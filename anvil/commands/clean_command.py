# Copyright 2012 Google Inc. All Rights Reserved.

"""Cleans all build-* paths and caches.
Attempts to delete all paths the build system creates.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import shutil
import sys

import anvil.commands.util as commandutil
from anvil.manage import ManageCommand


class CleanCommand(ManageCommand):
  def __init__(self):
    super(CleanCommand, self).__init__(
        name='clean',
        help_short='Cleans outputs and caches.',
        help_long=__doc__)

  def create_argument_parser(self):
    parser = super(CleanCommand, self).create_argument_parser()
    return parser

  def execute(self, args, cwd):
    result = commandutil.clean_output(cwd)
    return 0 if result else 1
