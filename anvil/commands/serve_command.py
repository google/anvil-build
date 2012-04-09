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
manage.py serve
manage.py serve --http_port=8080
# HTTP server + build daemon
manage.py serve :some_daemon
manage.py serve --http_port=8080 --daemon_port=8081 :some_daemon
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import argparse
import os
import sys

import anvil.commands.util as commandutil
from anvil.manage import manage_command


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('manage.py serve', __doc__)

  # Add all common args
  commandutil.add_common_build_args(parser, targets=True)

  # 'serve' specific

  return parser


@manage_command('serve', 'Continuously builds and serves targets.')
def serve(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  (result, all_target_outputs) = commandutil.run_build(cwd, parsed_args)

  print all_target_outputs

  return result
