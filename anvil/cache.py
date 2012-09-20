# Copyright 2012 Google Inc. All Rights Reserved.

"""Rule cache.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


class RuleCache(object):
  """
  """

  def __init__(self):
    """Initializes the rule cache.
    """
    pass

  def compute_delta(self, src_paths):
    """Computes a file delta for the given source paths.

    Args:
      src_paths: A list of fully-resolved source file paths.

    Returns:
      A FileDelta with the information from the given paths.
    """
    file_delta = FileDelta()
    file_delta.all_files.extend(src_paths)

    # TODO(benvanik): work
    file_delta.changed_files.extend(src_paths)

    return file_delta


class FileDelta(object):
  """
  """

  def __init__(self):
    """Initializes a file delta.
    """
    self.all_files = []
    self.added_files = []
    self.removed_files = []
    self.modified_files = []
    self.changed_files = []

  def any_changes(self):
    """
    Returns:
      True if any changes occurred.
    """
    return len(self.changed_files)
