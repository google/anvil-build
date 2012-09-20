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

  Outputs:
    All of the copied files in the output path.
  """

  def __init__(self, name, *args, **kwargs):
    """Initializes a copy files rule.

    Args:
      name: Rule name.
    """
    super(CopyFilesRule, self).__init__(name, *args, **kwargs)

  class _Context(RuleContext):
    def begin(self):
      super(CopyFilesRule._Context, self).begin()

      # Get all source -> output paths (and ensure directories exist)
      file_pairs = []
      for src_path in self.src_paths:
        out_path = self._get_out_path_for_src(src_path)
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


@build_rule('template_files')
class TemplateFilesRule(Rule):
  """Applies simple templating to a set of files.
  Processes each source file replacing a list of strings with corresponding
  strings.

  This uses the Python string templating functionality documented here:
  http://docs.python.org/library/string.html#template-strings

  Identifiers in the source template should be of the form "${identifier}", each
  of which maps to a key in the params dictionary.

  In order to prevent conflicts, it is strongly encouraged that a new_extension
  value is provided. If a source file has an extension it will be replaced with
  the specified one, and files without extensions will have it added.

  TODO(benvanik): more advanced template vars? perhaps regex?

  Inputs:
    srcs: Source file paths.
    new_extension: The extension to replace (or add) to all output files, with a
        leading dot ('.txt').
    params: A dictionary of key-value replacement parameters.

  Outputs:
    One file for each source file with the templating rules applied.
  """

  def __init__(self, name, new_extension=None, params=None, *args, **kwargs):
    """Initializes a file templating rule.

    Args:
      name: Rule name.
      new_extension: Replacement extension ('.txt').
      params: A dictionary of key-value replacement parameters.
    """
    super(TemplateFilesRule, self).__init__(name, *args, **kwargs)
    self.new_extension = new_extension
    self.params = params

  class _Context(RuleContext):
    def begin(self):
      super(TemplateFilesRule._Context, self).begin()

      # Get all source -> output paths (and ensure directories exist)
      file_pairs = []
      for src_path in self.src_paths:
        out_path = self._get_out_path_for_src(src_path)
        if self.rule.new_extension:
          out_path = os.path.splitext(out_path)[0] + self.rule.new_extension
        self._ensure_output_exists(os.path.dirname(out_path))
        self._append_output_paths([out_path])
        file_pairs.append((src_path, out_path))

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue templating task
      d = self._run_task_async(_TemplateFilesTask(
          self.build_env, file_pairs, self.rule.params))
      self._chain(d)


class _TemplateFilesTask(Task):
  def __init__(self, build_env, file_pairs, params, *args, **kwargs):
    super(_TemplateFilesTask, self).__init__(build_env, *args, **kwargs)
    self.file_pairs = file_pairs
    self.params = params

  def execute(self):
    for file_pair in self.file_pairs:
      with io.open(file_pair[0], 'rt') as f:
        template_str = f.read()
      template = string.Template(template_str)
      result_str = template.substitute(self.params)
      with io.open(file_pair[1], 'wt') as f:
        f.write(result_str)
    return True



@build_rule('strip_comments')
class StripCommentsRule(Rule):
  """Applies simple comment stripping to a set of files.
  Processes each source file removing C/C++-style comments.

  Note that this is incredibly hacky and may break in all sorts of cases.

  In order to prevent conflicts, it is strongly encouraged that a new_extension
  value is provided. If a source file has an extension it will be replaced with
  the specified one, and files without extensions will have it added.

  Inputs:
    srcs: Source file paths.
    new_extension: The extension to replace (or add) to all output files, with a
        leading dot ('.txt').

  Outputs:
    One file for each source file with the comments removed.
  """

  def __init__(self, name, new_extension=None, *args, **kwargs):
    """Initializes a comment stripping rule.

    Args:
      name: Rule name.
      new_extension: Replacement extension ('.txt').
    """
    super(StripCommentsRule, self).__init__(name, *args, **kwargs)
    self.new_extension = new_extension

  class _Context(RuleContext):
    def begin(self):
      super(StripCommentsRule._Context, self).begin()

      # Get all source -> output paths (and ensure directories exist)
      file_pairs = []
      for src_path in self.src_paths:
        out_path = self._get_out_path_for_src(src_path)
        if self.rule.new_extension:
          out_path = os.path.splitext(out_path)[0] + self.rule.new_extension
        self._ensure_output_exists(os.path.dirname(out_path))
        self._append_output_paths([out_path])
        file_pairs.append((src_path, out_path))

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      # Async issue stripping task
      d = self._run_task_async(_StripCommentsRuleTask(
          self.build_env, file_pairs))
      self._chain(d)


class _StripCommentsRuleTask(Task):
  def __init__(self, build_env, file_pairs, *args, **kwargs):
    super(_StripCommentsRuleTask, self).__init__(build_env, *args, **kwargs)
    self.file_pairs = file_pairs

  def execute(self):
    for file_pair in self.file_pairs:
      with io.open(file_pair[0], 'rt') as f:
        raw_str = f.read()

      # Code from Markus Jarderot, posted to stackoverflow
      def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return ""
        else:
            return s
      pattern = re.compile(
          r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
          re.DOTALL | re.MULTILINE)
      result_str = re.sub(pattern, replacer, raw_str)

      with io.open(file_pair[1], 'wt') as f:
        f.write(result_str)

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
