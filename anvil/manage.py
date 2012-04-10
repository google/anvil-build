#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Management shell script.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import fnmatch
import imp
import os
import sys

import util


def _get_anvil_path():
  """Gets the anvil/ path.

  Returns:
    The full path to the anvil/ source.
  """
  return os.path.normpath(os.path.dirname(__file__))


def manage_command(command_name, command_help=None):
  """A decorator for management command functions.
  Use this to register management command functions. A function decorated with
  this will be discovered and callable via manage.py.

  Functions are expected to take (args, cwd) and return an error number that
  will be passed back to the shell.

  Args:
    command_name: The name of the command exposed to the management script.
    command_help: Help text printed alongside the command when queried.
  """
  def _exec_command(fn):
    fn.command_name = command_name
    fn.command_help = command_help
    return fn
  return _exec_command


def discover_commands(search_path=None):
  """Looks for all commands and returns a dictionary of them.
  Commands are looked for under anvil/commands/, and should be functions
  decorated with @manage_command.

  Args:
    search_path: Search path to use instead of the default.

  Returns:
    A dictionary containing command-to-function mappings.

  Raises:
    KeyError: Multiple commands have the same name.
  """
  commands = {}
  if not search_path:
    commands_path = os.path.join(_get_anvil_path(), 'commands')
  else:
    commands_path = search_path
  for (root, dirs, files) in os.walk(commands_path):
    for name in files:
      if fnmatch.fnmatch(name, '*.py'):
        full_path = os.path.join(root, name)
        module = imp.load_source(os.path.splitext(name)[0], full_path)
        for attr_name in dir(module):
          if hasattr(getattr(module, attr_name), 'command_name'):
            command_fn = getattr(module, attr_name)
            command_name = command_fn.command_name
            if commands.has_key(command_name):
              raise KeyError('Command "%s" already defined' % (command_name))
            commands[command_name] = command_fn
  return commands


def usage(commands):
  """Gets usage info that can be displayed to the user.

  Args:
    commands: A command dictionary from discover_commands.

  Returns:
    A string containing usage info and a command listing.
  """
  s = 'manage.py command [-h]\n'
  s += '\n'
  s += 'Commands:\n'
  for command_name in commands:
    s += '  %s\n' % (command_name)
    command_help = commands[command_name].command_help
    if command_help:
      s += '    %s\n' % (command_help)
  return s


def run_command(args=None, cwd=None, commands=None):
  """Runs a command with the given context.

  Args:
    args: Arguments, with the command to execute as the first.
    cwd: Current working directory override.
    commands: A command dictionary from discover_commands to override the
        defaults.

  Returns:
    0 if the command succeeded and non-zero otherwise.

  Raises:
    ValueError: The command could not be found or was not specified.
  """
  args = args if args else []
  cwd = cwd if cwd else os.getcwd()

  commands = commands if commands else discover_commands()

  # TODO(benvanik): look for a .anvilrc, load it to find
  # - extra command search paths
  # - extra rule search paths
  # Also check to see if it was specified in args?

  if not len(args):
    raise ValueError('No command given')
  command_name = args[0]
  if not commands.has_key(command_name):
    raise ValueError('Command "%s" not found' % (command_name))

  command_fn = commands[command_name]
  return command_fn(args[1:], cwd)


def main(): # pragma: no cover
  """Entry point for scripts."""
  # Always add anvil/.. to the path
  sys.path.insert(1, _get_anvil_path())

  commands = discover_commands()

  try:
    return_code = run_command(args=sys.argv[1:],
                              cwd=os.getcwd(),
                              commands=commands)
  except ValueError:
    print usage(commands)
    return_code = 1
  except Exception as e:
    #print e
    raise
    return_code = 1
  sys.exit(return_code)


if __name__ == '__main__':
  main()
