"""Defines a package containing LogSink implementations.
"""

__author__ = 'joshharrison@google.com'


class PrintLogSink(object):
  """A very basic LogSink that simply prints to stdout.
  """
  def log(self, message):
    print '%s %s' % (message[1], message[3])
