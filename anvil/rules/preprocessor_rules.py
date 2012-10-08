# Copyright 2012 Google Inc. All Rights Reserved.

"""Simple preprocessor rules for the build system.
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


@build_rule('preprocess')
class PreprocessRule(Rule):
  """Applies simple C-style preprocessing to a set of files.
  Processes each source file handling the built-in preprocessor rules.

  Note that this is incredibly hacky and may break in all sorts of cases.

  In order to prevent conflicts, it is strongly encouraged that a new_extension
  value is provided. If a source file has an extension it will be replaced with
  the specified one, and files without extensions will have it added.

  Inputs:
    srcs: Source file paths.
    new_extension: The extension to replace (or add) to all output files, with a
        leading dot ('.txt').
    defines: A list of values to be defined by default.
        Example - 'DEBUG'.

  Outputs:
    One file for each source file after preprocessing.
  """

  def __init__(self, name, new_extension=None, defines=None, *args, **kwargs):
    """Initializes a preprocessing rule.

    Args:
      name: Rule name.
      new_extension: Replacement extension ('.txt').
      defines: A list of defines.
    """
    super(PreprocessRule, self).__init__(name, *args, **kwargs)
    self.new_extension = new_extension
    self.defines = defines[:] if defines else []

  class _Context(RuleContext):
    def begin(self):
      super(PreprocessRule._Context, self).begin()

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
      d = self._run_task_async(_PreprocessFilesTask(
          self.build_env, file_pairs, self.rule.defines))
      self._chain(d)


class _PreprocessFilesTask(Task):
  def __init__(self, build_env, file_pairs, defines, *args, **kwargs):
    super(_PreprocessFilesTask, self).__init__(build_env, *args, **kwargs)
    self.file_pairs = file_pairs
    self.defines = defines

  def execute(self):
    for file_pair in self.file_pairs:
      with io.open(file_pair[0], 'rt') as f:
        source_lines = f.readlines()

      result_str = self._preprocess(source_lines, self.defines)

      with io.open(file_pair[1], 'wt') as f:
        f.write(result_str)

    return True

  def _preprocess(self, source_lines, global_defines):
    # All defines in global + #defined in file
    file_defines = set(global_defines)

    # A stack of #ifdef scopes - for a given line to be included all must be
    # set to true
    inclusion_scopes = [True]

    target_lines = []
    for line in source_lines:
      line_included = all(inclusion_scopes)

      if line[0] == '#':
        line_included = False
        if line.startswith('#ifdef '):
          value = line[7:].strip()
          inclusion_scopes.append(value in file_defines)
        elif line.startswith('#else'):
          inclusion_scopes[-1] = not inclusion_scopes[-1]
        elif line.startswith('#endif'):
          inclusion_scopes.pop()
        elif line.startswith('#define '):
          value = line[8:].strip()
          file_defines.add(value)
        elif line.startswith('#undef '):
          value = line[7:].strip()
          file_defines.remove(value)

      if line_included:
        target_lines.append(line)

    return '\n'.join(target_lines)
