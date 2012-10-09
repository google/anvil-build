# Copyright 2012 Google Inc. All Rights Reserved.

"""Core rules for the build system.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import io
import os
import re
import shutil
import string

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task, ExecutableTask
import anvil.util


@build_rule('file_set')
class FileSetRule(Rule):
  """A file set aggregation rule.
  All source files are globbed together and de-duplicated before being passed
  on as outputs. If a src_filter is provided then it is used to filter all
  sources.

  File set rules can be used as synthetic rules for making dependencies easier
  to manage, or for filtering many rules into one.

  Inputs:
    srcs: Source file paths.

  Outputs:
    All of the source file paths, passed-through unmodified.
  """

  def __init__(self, name, *args, **kwargs):
    """Initializes a file set rule.

    Args:
      name: Rule name.
    """
    super(FileSetRule, self).__init__(name, *args, **kwargs)

  class _Context(RuleContext):
    def begin(self):
      super(FileSetRule._Context, self).begin()
      self._append_output_paths(self.src_paths)
      self._succeed()


@build_rule('copy_file')
class CopyFileRule(Rule):
  """Copies a single file into the given output path.
  This is like a

  This rule requires an explicit output path. If you want a more generalized
  copy rule see copy_files.

  Inputs:
    srcs: Source file path. Must only be one.
    base_path: Base path (one of 'gen', 'out', 'root').
    target: Target path.

  Outputs:
    The one copied file in the output path.
  """

  def __init__(self, name, base_path, target, *args, **kwargs):
    """Initializes a copy file rule.

    Args:
      name: Rule name.
      base_path: Base path (one of 'gen', 'out', 'root').
      target: Target path.
    """
    super(CopyFileRule, self).__init__(name, *args, **kwargs)
    self.base_path = base_path
    self.target = target

  class _Context(RuleContext):
    def begin(self):
      super(CopyFileRule._Context, self).begin()

      file_pairs = []

      # Get all source -> output paths (and ensure directories exist)
      src_path = self.src_paths[0]
      if self.rule.base_path == 'gen':
        out_path = self._get_gen_path(name=self.rule.target)
      elif self.rule.base_path == 'out':
        out_path = self._get_out_path(name=self.rule.target)
      else:
        out_path = self._get_root_path(name=self.rule.target)
      self._ensure_output_exists(os.path.dirname(out_path))
      self._append_output_paths([out_path])
      file_pairs.append((src_path, out_path))

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue copying task
      d = self._run_task_async(_CopyFilesTask(
          self.build_env, file_pairs))
      self._chain(d)


@build_rule('copy_files')
class CopyFilesRule(Rule):
  """Copy files from one path to another.
  Copies all source files to the output path.

  The resulting structure will match that of all files relative to the path of
  the module the rule is in. For example, srcs='a.txt' will result in
  '$out/a.txt', and srcs='dir/a.txt' will result in '$out/dir/a.txt'.

  If a src_filter is provided then it is used to filter all sources.

  This copies all files and preserves all file metadata, but does not preserve
  directory metadata.

  Inputs:
    srcs: Source file paths.
    out: Optional output path. If none is provided then the main output root
        will be used.
    flatten_paths: A list of paths to flatten into the root. For example,
        pass ['a/'] to flatten 'a/b/c.txt' to 'b/c.txt'

  Outputs:
    All of the copied files in the output path.
  """

  def __init__(self, name, out=None, flatten_paths=None, *args, **kwargs):
    """Initializes a copy files rule.

    Args:
      name: Rule name.
    """
    super(CopyFilesRule, self).__init__(name, *args, **kwargs)
    self.out = out
    self.flatten_paths = flatten_paths or []
    self.flatten_paths = [path.replace('/', os.path.sep)
                          for path in self.flatten_paths]

  class _Context(RuleContext):
    def begin(self):
      super(CopyFilesRule._Context, self).begin()

      # Get all source -> output paths (and ensure directories exist)
      file_pairs = []
      for src_path in self.src_paths:
        rel_path = os.path.relpath(src_path, self.build_env.root_path)
        rel_path = anvil.util.strip_build_paths(rel_path)
        for prefix in self.rule.flatten_paths:
          rel_path = rel_path.replace(prefix, '')
        rel_path = os.path.normpath(rel_path)
        if self.rule.out:
          out_path = os.path.join(self.rule.out, rel_path)
          out_path = self._get_out_path(name=out_path)
        else:
          out_path = self._get_out_path_for_src(
              os.path.join(self.build_env.root_path, rel_path))
        self._ensure_output_exists(os.path.dirname(out_path))
        self._append_output_paths([out_path])
        file_pairs.append((src_path, out_path))

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue copying task
      d = self._run_task_async(_CopyFilesTask(
          self.build_env, file_pairs))
      self._chain(d)


class _CopyFilesTask(Task):
  def __init__(self, build_env, file_pairs, *args, **kwargs):
    super(_CopyFilesTask, self).__init__(build_env, *args, **kwargs)
    self.file_pairs = file_pairs

  def execute(self):
    for file_pair in self.file_pairs:
      shutil.copy2(file_pair[0], file_pair[1])
    return True


@build_rule('concat_files')
class ConcatFilesRule(Rule):
  """Concatenate many files into one.
  Takes all source files and concatenates them together. The order is based on
  the ordering of the srcs list, and all files are treated as binary.

  Note that if referencing other rules or globs the order of files may be
  undefined, so if order matters try to enumerate files manually.

  TODO(benvanik): support a text mode?

  Inputs:
    srcs: Source file paths. The order is the order in which they will be
        concatenated.
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    All of the srcs concatenated into a single file path. If no out is specified
    a file with the name of the rule will be created.
  """

  def __init__(self, name, out=None, *args, **kwargs):
    """Initializes a concatenate files rule.

    Args:
      name: Rule name.
      out: Optional output name.
    """
    super(ConcatFilesRule, self).__init__(name, *args, **kwargs)
    self.out = out

  class _Context(RuleContext):
    def begin(self):
      super(ConcatFilesRule._Context, self).begin()

      output_path = self._get_out_path(name=self.rule.out)
      self._ensure_output_exists(os.path.dirname(output_path))
      self._append_output_paths([output_path])

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue concat task
      d = self._run_task_async(_ConcatFilesTask(
          self.build_env, self.src_paths, output_path))
      self._chain(d)


class _ConcatFilesTask(Task):
  def __init__(self, build_env, src_paths, output_path, *args, **kwargs):
    super(_ConcatFilesTask, self).__init__(build_env, *args, **kwargs)
    self.src_paths = src_paths
    self.output_path = output_path

  def execute(self):
    with io.open(self.output_path, 'wt') as out_file:
      for src_path in self.src_paths:
        with io.open(src_path, 'rt') as in_file:
          out_file.write(in_file.read())
    return True


@build_rule('shell_execute')
class ShellExecuteRule(Rule):
  """Executes a command on the shell.

  Inputs:
    srcs: Source file paths. These will be appended to the command line.
    command: A list of arguments to execute.

  Outputs:
    None?
  """

  def __init__(self, name, command, *args, **kwargs):
    """Initializes a shell execute rule.

    Args:
      name: Rule name.
      command: Command arguments.
    """
    super(ShellExecuteRule, self).__init__(name, *args, **kwargs)
    self.command = command

  class _Context(RuleContext):
    def begin(self):
      super(ShellExecuteRule._Context, self).begin()

      # Build command line
      executable_name = self.rule.command[0]
      call_args = self.rule.command[1:]
      call_args.extend(self.src_paths)

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue copying task
      d = self._run_task_async(ExecutableTask(
          self.build_env, executable_name, call_args))
      self._chain(d)
