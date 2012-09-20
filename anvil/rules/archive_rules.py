# Copyright 2012 Google Inc. All Rights Reserved.

"""Rules for archiving files.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import io
import os
import shutil
import string
import zipfile

import anvil.util
from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task


@build_rule('archive_files')
class ArchiveFilesRule(Rule):
  """Zip up files into an archive.
  Archives all files into a zip file. build- paths are flattened.

  Inputs:
    srcs: Source file paths.
    out: Optional output name. If none is provided than the rule name will be
        used.
    flatten_paths: A list of paths to flatten into the root. For example,
        pass ['a/'] to flatten 'a/b/c.txt' to 'b/c.txt'

  Outputs:
    All of the srcs archived into a single zip file. If no out is specified
    a file with the name of the rule will be created.
  """

  def __init__(self, name, out=None, flatten_paths=None, *args, **kwargs):
    """Initializes an archive files rule.

    Args:
      name: Rule name.
      out: Optional output name.
    """
    super(ArchiveFilesRule, self).__init__(name, *args, **kwargs)
    self.out = out
    self.flatten_paths = flatten_paths or []
    self.flatten_paths = [path.replace('/', os.path.sep)
                          for path in self.flatten_paths]

  class _Context(RuleContext):
    def begin(self):
      super(ArchiveFilesRule._Context, self).begin()

      output_path = self._get_out_path(name=self.rule.out, suffix='.zip')
      self._ensure_output_exists(os.path.dirname(output_path))
      self._append_output_paths([output_path])

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Compute the relative archive path for each file
      paths = []
      for src_path in self.src_paths:
        rel_path = os.path.relpath(src_path, self.build_env.root_path)
        rel_path = anvil.util.strip_build_paths(rel_path)
        for prefix in self.rule.flatten_paths:
          rel_path = rel_path.replace(prefix, '')
        paths.append((src_path, rel_path))

      # Async issue archive task
      d = self._run_task_async(_ArchiveFilesTask(
          self.build_env, paths, output_path))
      self._chain(d)


class _ArchiveFilesTask(Task):
  def __init__(self, build_env, paths, output_path, *args, **kwargs):
    super(_ArchiveFilesTask, self).__init__(build_env, *args, **kwargs)
    self.paths = paths
    self.output_path = output_path

  def execute(self):
    f = zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED)
    try:
      for path in self.paths:
        (src_path, rel_path) = path
        f.write(src_path, rel_path)
    except:
      f.close()
    return True
