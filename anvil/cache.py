# Copyright 2012 Google Inc. All Rights Reserved.

"""Rule cache.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import cPickle
import os


class RuleCache(object):
  """Abstract rule cache.
  """

  def __init__(self, *args, **kwargs):
    """Initializes the rule cache.
    """
    pass

  def save(self):
    """Saves the cache off to disk.
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
    file_delta.changed_files.extend(src_paths)
    return file_delta


class FileRuleCache(RuleCache):
  """File-based rule cache.
  """

  def __init__(self, cache_path, *args, **kwargs):
    """Initializes the rule cache.

    Args:
      cache_path: Path to store the cache file in.
    """
    super(FileRuleCache, self).__init__(self, *args, **kwargs)
    self.cache_path = os.path.join(cache_path, '.anvil-cache')
    self.data = dict()
    self._dirty = False

    if os.access(self.cache_path, os.R_OK):
      with open(self.cache_path, 'rb') as file_obj:
        self.data.update(cPickle.load(file_obj))

  def save(self):
    if not self._dirty:
      return
    self._dirty = False
    with open(self.cache_path, 'wb') as file_obj:
      cPickle.dump(self.data, file_obj, 2)

  def compute_delta(self, src_paths):
    file_delta = FileDelta()
    file_delta.all_files.extend(src_paths)

    # TODO(benvanik): work
    self._dirty = True
    file_delta.changed_files.extend(src_paths)

    return file_delta


class FileDelta(object):
  """File delta information.
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
