# Copyright 2012 Google Inc. All Rights Reserved.

"""Launches an HTTP server and optionally a continuous build daemon.
This serves the current working directory over HTTP, similar to Python's
SimpleHTTPServer.

If a daemon port and any rules are defined then changes to the
specified paths will automatically trigger builds. A WebSocket port is specified
that clients can connect to and get lists of file change sets.

Daemon rules should be of the form:
file_set('some_daemon',
         srcs=['watch_path_1/', 'watch_path_2/'],
         deps=[':root_build_target'])
Where the given srcs will be recursively watched for changes to trigger the
rules specified in deps.

Examples:
# Simple HTTP server
anvil serve
anvil serve --http_port=8080
# HTTP server + build daemon
anvil serve :some_daemon
anvil serve --http_port=8080 --daemon_port=8081 :some_daemon
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import sys

import anvil.commands.util as commandutil
from anvil.manage import ManageCommand


class ServeCommand(ManageCommand):
  def __init__(self):
    super(ServeCommand, self).__init__(
        name='serve',
        help_short='Continuously builds and serves targets.',
        help_long=__doc__)
    self._add_common_build_hints()

  def create_argument_parser(self):
    parser = super(ServeCommand, self).create_argument_parser()

    # Add all common args
    self._add_common_build_arguments(parser, targets=True)

    # 'serve' specific

    return parser

  def execute(self, args, cwd):
    # Handle --rebuild
    if args.rebuild:
      if not commandutil.clean_output(cwd):
        return False

    (result, all_target_outputs) = commandutil.run_build(cwd, args)

    print all_target_outputs

    return 0 if result else 1
