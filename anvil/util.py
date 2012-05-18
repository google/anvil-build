# Copyright 2012 Google Inc. All Rights Reserved.

__author__ = 'benvanik@google.com (Ben Vanik)'


import inspect
import os
import re
import string
import sys
import time


# Unfortunately there is no one-true-timer in python
# This should always be preferred over direct use of the time module
if sys.platform == 'win32' or sys.platform == 'cygwin':
  timer = time.clock # pragma: no cover
else:
  timer = time.time # pragma: no cover


def get_anvil_path():
  """Gets the anvil/ path.

  Returns:
    The full path to the anvil/ source.
  """
  return os.path.normpath(os.path.dirname(__file__))


def get_script_path():
  """Gets the absolute parent path of the currently executing script.

  Returns:
    Absolute path of the calling file.
  """
  return os.path.dirname(os.path.abspath(inspect.stack()[1][1]))


def strip_build_paths(path):
  """Strips out build-*/ from the given path.

  Args:
    path: Path that may contain build-*/.

  Returns:
    The path with build-*/ removed.
  """
  strip_paths = [
      'build-out%s' % os.sep,
      'build-gen%s' % os.sep,
      'build-out%s' % os.altsep,
      'build-gen%s' % os.altsep,
      ]
  for strip_path in strip_paths:
    path = path.replace(strip_path, '')
  return path


def is_rule_path(value):
  """Detects whether the given value is a rule name.

  Returns:
    True if the string is a valid rule name.
  """
  if not isinstance(value, str) or not len(value):
    return False
  semicolon = string.rfind(value, ':')
  if semicolon < 0:
    return False
  # Must be just a valid literal after, no path separators
  if (string.find(value, '\\', semicolon) >= 0 or
      string.find(value, '/', semicolon) >= 0):
    return False
  return True


def validate_names(values, require_semicolon=False):
  """Validates a list of rule names to ensure they are well-defined.

  Args:
    values: A list of values to validate.
    require_semicolon: Whether to require a :

  Raises:
    NameError: A rule value is not valid.
    TypeError: The type of values is incorrect.
  """
  if not values:
    return
  for value in values:
    if not isinstance(value, str) or not len(value):
      raise TypeError('Names must be a string of non-zero length')
    if len(value.strip()) != len(value):
      raise NameError(
          'Names cannot have leading/trailing whitespace: "%s"' % (value))
    if require_semicolon and not is_rule_path(value):
      raise NameError('Names must be a rule (contain a :): "%s"' % (value))


def underscore_to_pascalcase(value):
  """Converts a string from underscore_case to PascalCase.

  Args:
    value: Source string value.
        Example - hello_world

  Returns:
    The string, converted to PascalCase.
    Example - hello_world -> HelloWorld
  """
  if not value:
    return value
  def __CapWord(seq):
    for word in seq:
      yield word.capitalize()
  return ''.join(__CapWord(word if word else '_' for word in value.split('_')))


def which(executable_name):
  """Gets the full path to the given executable.
  If the given path exists in the CWD or is already absolute it is returned.
  Otherwise this method will look through the system PATH to try to find it.

  Args:
    executable_name: Name or path to the executable.

  Returns:
    The full path to the executable or None if it was not found.
  """
  if (os.path.exists(executable_name) and
      not os.path.isdir(executable_name)):
    return os.path.abspath(executable_name)
  for path in os.environ.get('PATH', '').split(os.pathsep):
    if (os.path.exists(os.path.join(path, executable_name)) and
        not os.path.isdir(os.path.join(path, executable_name))):
      return os.path.join(path, executable_name)
  return None
