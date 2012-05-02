# Copyright 2012 Google Inc. All Rights Reserved.

__author__ = 'benvanik@google.com (Ben Vanik)'


import ConfigParser
import io
import os


_DEFAULT_NAME = '.anvilrc'


def _scan_up(path, target_name):
  """Recursively scans up the path looking for the given file.

  Args:
    path: Directory to search.
    target_name: Target file name to find.

  Returns:
    A full file path if the file is found, otherwise None.
  """
  if not len(path) or path == '/':
    return None
  self_path = os.path.join(path, target_name)
  if os.path.isfile(self_path):
    return self_path
  return _scan_up(os.path.dirname(path), target_name)


def _scan_up_all(path, target_name):
  """Recursively scans up the entire path chain, finding all files with the
  given name.

  Args:
    path: Directory to search.
    target_name: Target file name to find.

  Returns:
    A list of full file paths for each file found. May be empty.
  """
  file_paths = []
  while True:
    file_path = _scan_up(path, target_name)
    if not file_path:
      break
    file_paths.append(file_path)
    path = os.path.dirname(os.path.dirname(file_path))
  file_paths.reverse()
  return file_paths


def load(path):
  """Loads all config files, including those up the directory path and in the
  user profile path.

  Args:
    path: Path to search for the config file.

  Returns:
    An initialized Config object or None if no config was found.
  """
  file_paths = _scan_up_all(path, _DEFAULT_NAME)
  file_paths.append(os.path.expanduser('~/%s' % _DEFAULT_NAME))

  config = ConfigParser.SafeConfigParser()
  config.read(file_paths)
  return config
