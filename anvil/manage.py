#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Management shell script.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import argparse
import fnmatch
import imp
import io
import os
import re
import sys

import util


# Hack to get formatting in usage() correct
class _ComboHelpFormatter(argparse.RawDescriptionHelpFormatter,
                          argparse.ArgumentDefaultsHelpFormatter):
  pass


class ManageCommand(object):
  """Base type for manage commands.
  All subclasses of this type can be auto-discovered and added to the command
  list.
  """

  def __init__(self, name, help_short=None, help_long=None, *args, **kwargs):
    """Initializes a manage command.

    Args:
      name: The name of the command exposed to the management script.
      help_short: Help text printed alongside the command when queried.
      help_long: Extended help text when viewing command help.
    """
    self.name = name
    self.help_short = help_short
    self.help_long = help_long

  def create_argument_parser(self):
    """Creates and sets up an argument parser.

    Returns:
      An ready to use ArgumentParser.
    """
    parser = argparse.ArgumentParser(prog='anvil %s' % (self.name),
                                     description=self.help_long,
                                     formatter_class=_ComboHelpFormatter)
    # TODO(benvanik): add common arguments (logging levels/etc)
    return parser

  def _add_common_build_arguments(self, parser, targets=False):
    """Adds common build arguments to an argument parser.

    Args:
      parser: ArgumentParser to modify.
      targets: True to add variable target arguments.
    """
    # Threading/execution control
    parser.add_argument('-j', '--jobs',
                        dest='jobs',
                        type=int,
                        default=None,
                        help=('Specifies the number of tasks to run '
                              'simultaneously. If omitted then all processors '
                              'will be used.'))

    # Build context control
    parser.add_argument('-f', '--force',
                        dest='force',
                        action='store_true',
                        default=False,
                        help=('Force all rules to run as if there was no '
                              'cache.'))
    parser.add_argument('--stop_on_error',
                        dest='stop_on_error',
                        action='store_true',
                        default=False,
                        help=('Stop building when an error is encountered.'))

    # Target specification
    if targets:
      parser.add_argument('targets',
                          nargs='+',
                          metavar='target',
                          help='Target build rule (such as :a or foo/bar:a)')

  def execute(self, args, cwd):
    """Executes the command.

    Args:
      args: ArgumentParser parsed argument object.
      cwd: Current working directory.

    Returns:
      Return code of the command.
    """
    return 1


def discover_commands(search_path=None):
  """Looks for all commands and returns a dictionary of them.
  Commands are discovered in the given search path (or anvil/commands/) by
  looking for subclasses of ManageCommand.

  Args:
    search_path: Search path to use instead of the default.

  Returns:
    A dictionary containing name-to-ManageCommand mappings.

  Raises:
    KeyError: Multiple commands have the same name.
  """
  commands = {}
  if not search_path:
    commands_path = os.path.join(util.get_anvil_path(), 'commands')
  else:
    commands_path = search_path
  for (root, dirs, files) in os.walk(commands_path):
    for name in files:
      if fnmatch.fnmatch(name, '*.py'):
        full_path = os.path.join(root, name)
        module = imp.load_source(os.path.splitext(name)[0], full_path)
        for attr_name in dir(module):
          command_cls = getattr(module, attr_name)
          # HACK(benvanik): remove this hack after module naming is cleaned up
          # if (isinstance(command_cls, type) and
          #     issubclass(command_cls, ManageCommand)):
          if isinstance(command_cls, type):
            import anvil.manage
            if (command_cls != anvil.manage.ManageCommand and
                issubclass(command_cls, anvil.manage.ManageCommand)):
              command = command_cls()
              command_name = command.name
              if commands.has_key(command_name):
                raise KeyError('Command "%s" already defined' % (command_name))
              commands[command_name] = command
  return commands


def usage(commands=None):
  """Gets usage info that can be displayed to the user.

  Args:
    commands: A command dictionary from discover_commands.

  Returns:
    A string containing usage info and a command listing.
  """
  commands = commands if commands else discover_commands()

  s = 'anvil command [-h]\n'
  s += '\n'
  s += 'Commands:\n'
  command_names = commands.keys()
  command_names.sort()
  for command_name in command_names:
    s += '  %s\n' % (command_name)
    command_help = commands[command_name].help_short
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

  # TODO(benvanik): if a command is specified try loading it first - may be
  #     able to avoid searching all commands
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

  command = commands[command_name]
  parser = command.create_argument_parser()
  parsed_args = parser.parse_args(args[1:])
  return command.execute(args=parsed_args, cwd=cwd)


def autocomplete(words, cword, cwd, commands=None):
  """Completes the given command string.

  Args:
    words: A list of all words in the current command line (minus the prog).
        COMP_WORDS split and with the first argument (app name) removed.
    cword: An index into words indicating the cursor position.
        COMP_CWORD in integer form.
    cwd: Current working directory.

  Returns:
    A space-delimited string of completion words for the current command line.
  """
  # TODO(benvanik): if a command is specified try loading it first - may be
  #     able to avoid searching all commands
  commands = commands if commands else discover_commands()

  try:
    current = words[cword]
  except IndexError:
    current = ''
  try:
    previous = words[cword - 1]
  except IndexError:
    previous = ''

  if cword == 0:
    # At the first word, which is the command
    # Attempt to autocomplete one if it's in progress, or just list them out
    return ' '.join([c for c in commands.keys() if c.startswith(current)])

  # Somewhere inside of a command
  if not commands.has_key(words[0]):
    # Whatever the user is typing is not recognized
    return None
  command = commands[words[0]]

  if current.startswith('-') or current.startswith('--'):
    # TODO(benvanik): pull out options from ArgumentParser
    cs = ['--a', '--b', '-c']
    return ' '.join([c for c in cs if c.startswith(current)])

  # Bash treats ':' as a separator and passes in things like 'a:b' as [a,:,b]
  # So, look for current = ':' and prev = ':' to try to find out if we are
  # referencing rules

  target_module = ''
  rule_prefix = ''
  if previous == ':':
    rule_prefix = current
    current = ':'
    try:
      previous = words[cword - 2]
    except IndexError:
      previous = ''
  if current == ':':
    if len(previous):
      # If previous refers to a module, get all rules from it
      target_module = os.path.normpath(os.path.join(cwd, previous))
    else:
      # If there is a BUILD file in the current path, get all rules from it
      target_module = cwd
  if len(target_module):
    if os.path.isdir(target_module):
      target_module = os.path.join(target_module, 'BUILD')
    if os.path.isfile(target_module):
      # Module exists! Extract the rules and return them
      # TODO(benvanik): maybe load the module? that requires a lot more work...
      with io.open(target_module, 'r') as f:
        module_str = f.read()
      all_rules = []
      for rule_match in re.finditer(r'name=[\'\"]([a-zA-Z0-9_]+)[\'\"]',
                                    module_str,
                                    flags=re.MULTILINE):
        rule_name = rule_match.group(1)
        all_rules.append(rule_name)
      return ' '.join([c for c in all_rules if c.startswith(rule_prefix)])
    # Bad - prevent any more completion on this block
    # TODO(benvanik): how do you prevent completion?!
    return None

  # Nothing we know or care about - allow bash to take over
  return None


def main(): # pragma: no cover
  """Entry point for scripts."""
  # Always add anvil/.. to the path
  sys.path.insert(1, util.get_anvil_path())

  commands = discover_commands()

  # Run auto-completion logic
  if 'ANVIL_AUTO_COMPLETE' in os.environ:
    match_str = autocomplete(
        words=os.environ['COMP_WORDS'].split(' ')[1:],
        cword=int(os.environ['COMP_CWORD']) - 1,
        cwd=os.getcwd(),
        commands=commands)
    if match_str and len(match_str):
      print match_str
    sys.exit(1)

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
  # Always add anvil/.. to the path
  sys.path.insert(1, os.path.join(util.get_anvil_path(), '..'))
  main()
