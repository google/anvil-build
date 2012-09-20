# Copyright 2012 Google Inc. All Rights Reserved.

"""Rule cache.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import base64
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

  def compute_delta(self, rule_path, mode, src_paths):
    """Computes a file delta for the given source paths.

    Args:
      rule_path: Full path to the rule.
      mode: Mode indicating which type of set to use.
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

    if os.path.exists(self.cache_path):
      with open(self.cache_path, 'rb') as file_obj:
        self.data.update(cPickle.load(file_obj))

  def save(self):
    if not self._dirty:
      return
    self._dirty = False
    try:
      os.makedirs(os.path.split(self.cache_path)[0])
    except:
      pass
    with open(self.cache_path, 'wb') as file_obj:
      cPickle.dump(self.data, file_obj, 2)

  def compute_delta(self, rule_path, mode, src_paths):
    file_delta = FileDelta()
    file_delta.all_files.extend(src_paths)

    # Scan all files - we need this to compare regardless of whether we have
    # data from the cache
    # TODO(benvanik): make this parallel
    new_data = dict()
    for src_path in src_paths:
      file_time = os.path.getmtime(src_path)
      file_size = os.path.getsize(src_path)
      new_data[src_path] = '%s-%s' % (file_time, file_size)

    # Always swap for new data
    key = base64.b64encode('%s->%s' % (rule_path, mode))
    old_data = self.data.get(key, None)
    self.data[key] = new_data

    # No previous data - ignore
    if not old_data:
      self._dirty = True
      file_delta.changed_files.extend(src_paths)
      return file_delta

    # Compare data

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
