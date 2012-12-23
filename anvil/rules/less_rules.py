# Copyright 2012 Google Inc. All Rights Reserved.

"""LESS stylesheets rules for the build system.

Contains the following rules:
less_css_library
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task, NodeExecutableTask


@build_rule('less_css_library')
class LessCssLibraryRule(Rule):
  """A LESS transformed file.
  Uses the LESS compiler to process an input LESS file into a
  single output CSS file.

  Only the first source will be used as the root to less. The rest will be
  treated as dependencies.

  Inputs:
    srcs: The root LESS file..
    include_paths: Paths to search for include files.
    compiler_flags: A list of string compiler flags.
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    A single compiled CSS file. If no out is specified a file with the name of
    the rule will be created.
  """

  def __init__(self, name, include_paths=None,
      compiler_flags=None, out=None, *args, **kwargs):
    """Initializes a LESS CSS rule.

    Args:
      srcs: The root LESS file.
      include_paths: Paths to search for include files.
      compiler_flags: A list of string compiler flags.
      out: Optional output name. If none is provided than the rule name will be
          used.
    """
    super(LessCssLibraryRule, self).__init__(name, *args, **kwargs)

    self.include_paths = []
    if include_paths:
        self.include_paths.extend(include_paths)
    self._append_dependent_paths(self.include_paths)

    self.compiler_flags = []
    if compiler_flags:
      self.compiler_flags.extend(compiler_flags)

    self.out = out

  class _Context(RuleContext):
    def begin(self):
      super(LessCssLibraryRule._Context, self).begin()

      args = [
      ]
      args.extend(self.rule.compiler_flags)

      if len(self.rule.include_paths):
        args.append('--include-path=%s' % (
            ':'.join(self.rule.include_paths)))

      output_path = self._get_out_path(name=self.rule.out, suffix='.css')
      self._ensure_output_exists(os.path.dirname(output_path))
      self._append_output_paths([output_path])

      args.append(self.src_paths[0])
      args.append(output_path)

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      d = self._run_task_async(NodeExecutableTask(
          self.build_env, 'node_modules/less/bin/lessc', args))
      # TODO(benvanik): pull out (stdout, stderr) from result and the exception
      #     to get better error logging
      self._chain(d)
