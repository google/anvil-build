# Copyright 2012 Google Inc. All Rights Reserved.

"""Provides scripts to enable shell completion.
To enable completion at startup, run the following (under bash):
$ anvil completion --bash >> ~/.profile

If you prefer to only have it in the current session:
$ eval "`anvil completion --bash`"

If you want it globally installed (to /etc/bash_completion.d):
$ sudo anvil completion --install --bash
"""

# Portions of this file are inspired by optcomplete and pip

__author__ = 'benvanik@google.com (Ben Vanik)'


import io
import os
import sys

import anvil.commands.util as commandutil
from anvil.manage import manage_command


class _ShellCompletion(object):
  """Base type for shell completion setup utilities.
  """

  def get_profile_string(self):
    """Gets a string that can be placed in a .profile.

    Returns:
      A string in the current shell language for setting up completion.
    """
    raise NotImplementedError()

  def install(self):
    """Installs a global completion script, if possible.
    This will generally require root access and should warn appropriately.

    Returns:
      True if the install was successful.
    """
    raise NotImplementedError()


class _BashCompletion(_ShellCompletion):
  """Bash shell completion utilities.
  """

  _completion_str = """
_anvil_completion()
{
  COMPREPLY=($(COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD \\
               ANVIL_AUTO_COMPLETE=1 $1))
}
complete -o default -F _anvil_completion anvil
"""

  def get_profile_string(self):
    return """
# > anvil-build completion script%s# < anvil-build completion script
""" % self._completion_str

  def install(self):
    file_str = """# Copyright 2012 Google Inc. All Rights Reserved.

# Bash completion script for anvil-build
%s
""" % (self._completion_str)
    try:
      with io.open('/etc/bash_completion.d/anvil', 'wb') as f:
        f.write(file_str)
      print 'Successfully installed to /etc/bash_completion.d/'
      print 'Restart your shell or run the following to start completing:'
      print '$ source /etc/bash_completion.d/anvil'
      return True
    except IOError as e:
      print e
      print 'error: unable to write to /etc/bash_completion.d/'
      print '       try running with sudo!'
      return False


_COMPLETIONS = {
    'bash': _BashCompletion(),
    }


def _get_options_parser():
  """Gets an options parser for the given args."""
  parser = commandutil.create_argument_parser('anvil completion', __doc__)

  # 'completion' specific
  parser.add_argument('--install',
                      dest='install',
                      action='store_true',
                      default=False,
                      help=('Install the completion script to the global path, '
                            'such as /etc/bash_completion.d/'))
  parser.add_argument('--bash',
                      dest='shell',
                      action='store_const',
                      const='bash',
                      help=('Generate completion code for bash.'))
  # TODO(benvanik): other shells? are there even any others that people use?

  return parser


@manage_command('completion', 'Provides scripts to enable shell completion.')
def completion(args, cwd):
  parser = _get_options_parser()
  parsed_args = parser.parse_args(args)

  if not parsed_args.shell:
    parser.print_help()
    print '\nerror: please specify a shell (such as --bash)'
    return False

  if not _COMPLETIONS.has_key(parsed_args.shell):
    parser.print_help()
    print '\nerror: shell environment "%s" not supported' % (parsed_args.shell)
    return False

  completion = _COMPLETIONS[parsed_args.shell]
  if parsed_args.install:
    return completion.install()
  else:
    print completion.get_profile_string()

  return True
