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


import copy
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
    self._add_common_build_arguments(
        parser, targets=True, targets_optional=True)

    # 'serve' specific
    parser.add_argument('-p', '--http_port',
                        dest='http_port',
                        type=int,
                        default=8080,
                        help=('TCP port the HTTP server will listen on.'))

    return parser

  def execute(self, args, cwd):
    # Initial build
    if len(args.targets):
      (result, all_target_outputs) = commandutil.run_build(cwd, args)
      print(all_target_outputs)

    self._launch_http_server(args.http_port, cwd)

    return 0

  def _launch_http_server(self, port, root_path):
    """Launches a simple static twisted HTTP server.
    The server will automatically merge build-* paths in to a unified namespace.

    Args:
      port: TCP port to listen on.
      root_path: Root path of the HTTP server.
    """
    # Twisted has a bug where it doesn't properly initialize mimetypes
    # This must be done before importing it
    import mimetypes
    mimetypes.init()

    from twisted.internet import reactor
    from twisted.web.resource import Resource, NoResource
    from twisted.web.server import Site
    from twisted.web.static import File

    # Special site handler that merges various output and input paths into a
    # single unifed file system
    class MergedSite(Site):
      def getResourceFor(self, request):
        # Scan well-known search paths first
        search_paths = ['build-out', 'build-gen',]
        for search_path in search_paths:
          resource = self.resource
          prepath = copy.copy(request.prepath)
          postpath = copy.copy(request.postpath)
          postpath.insert(0, search_path)
          while postpath and not resource.isLeaf:
            path_element = postpath.pop(0)
            prepath.append(path_element)
            resource = resource.getChildWithDefault(path_element, request)
          if resource and not isinstance(resource, NoResource):
            return resource
        # Fallback to normal handling
        return Site.getResourceFor(self, request)

    print('Launching HTTP server on port %s...' % (port))

    root = File(root_path)
    factory = MergedSite(root)
    reactor.listenTCP(port, factory)
    reactor.run()
