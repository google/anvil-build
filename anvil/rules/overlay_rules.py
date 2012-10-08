# Copyright 2012 Google Inc. All Rights Reserved.

"""Merged path view rules for the build system.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task
import anvil.util


@build_rule('overlay_view')
class OverlayViewRule(Rule):
  """Constructs or updates an view over merged paths.
  This uses system symlinks to build a path that contains access to all source
  paths as if they existed side-by-side. This only needs to be re-run when
  file structure changes, and allows for access to files at their sources
  (adding edit-reloadability).

  Inputs:
    srcs: Source file paths. All of the files that will be available.
    out: Optional output name. If none is provided than the rule name will be
        used.
    flatten_paths: A list of paths to flatten into the root. For example,
        pass ['a/'] to flatten 'a/b/c.txt' to 'b/c.txt'

  Outputs:
    Merged directory filled with symlinks.
  """

  def __init__(self, name, out=None, flatten_paths=None, *args, **kwargs):
    """Initializes an overlay view rule.

    Args:
      name: Rule name.
      out: Optional output name. If none is provided than the rule name will be
        used.
    """
    super(OverlayViewRule, self).__init__(name, *args, **kwargs)
    self.out = out
    self.flatten_paths = flatten_paths or []
    self.flatten_paths = [path.replace('/', os.path.sep)
                          for path in self.flatten_paths]

  class _Context(RuleContext):
    def begin(self):
      super(OverlayViewRule._Context, self).begin()

      # Could, if output exists, only modify added/removed symlinks
      # file_delta = self.file_delta
      # file_delta.added_files
      # file_delta.removed_files

      # Ensure output exists
      output_path = self._get_root_path(name=self.rule.out)
      self._ensure_output_exists(output_path)
      self._append_output_paths([output_path])

      # Compute the relative path for each file
      paths = []
      for src_path in self.src_paths:
        rel_path = os.path.relpath(src_path, self.build_env.root_path)
        rel_path = anvil.util.strip_build_paths(rel_path)
        for prefix in self.rule.flatten_paths:
          rel_path = rel_path.replace(prefix, '')
        paths.append((src_path, rel_path))

      # Async issue linking task
      d = self._run_task_async(_SymlinkTask(
          self.build_env, paths, output_path))
      self._chain(d)


class _SymlinkTask(Task):
  def __init__(self, build_env, paths, output_path, *args, **kwargs):
    super(_SymlinkTask, self).__init__(build_env, *args, **kwargs)
    self.paths = paths
    self.output_path = output_path

  def execute(self):
    # Tracks all exists checks on link parent paths
    checked_dirs = {}

    for path in self.paths:
      (src_path, rel_path) = path
      link_path = os.path.join(self.output_path, rel_path)
      if not os.path.exists(link_path):
        # Ensure parent of link path exists
        link_parent = os.path.dirname(link_path)
        if not checked_dirs.get(link_parent, False):
          if not os.path.exists(link_parent):
            os.makedirs(link_parent)
          checked_dirs[link_parent] = True

        os.symlink(src_path, link_path)

    return True
