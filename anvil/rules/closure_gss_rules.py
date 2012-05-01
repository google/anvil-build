# Copyright 2012 Google Inc. All Rights Reserved.

"""Closure compiler rules for the build system.

Contains the following rules:
closure_gss
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task, JavaExecutableTask


@build_rule('closure_gss')
class ClosureGssRule(Rule):
  """A Closure Stylesheets transformed file.
  Uses the Closure Stylesheets compiler to cat/minify input GSS files into a
  single output CSS file.

  The input order of the GSS files matters. Dependent files must be provided
  before the files that depend on them.

  Inputs:
    srcs: All source GSS files, in order.
    mode: Minification mode, one of ['MINIFIED', 'DEBUG_COMPILED', 'COMPILED'].
    compiler_jar: Path to a compiler .jar file.
    pretty_print: True to pretty print the output.
    defines: A list of defines for conditional operators.
    compiler_flags: A list of string compiler flags.
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    A single compiled CSS file. If no out is specified a file with the name of
    the rule will be created. If enabled, a naming map JS file will also be
    emitted.
  """

  def __init__(self, name, mode, compiler_jar,
      pretty_print=False, defines=None, compiler_flags=None, out=None,
      *args, **kwargs):
    """Initializes a Closure GSS rule.

    Args:
      srcs: All source GSS files, in order.
      mode: Minification mode, one of ['MINIFIED', 'DEBUG_COMPILED',
          'COMPILED'].
      compiler_jar: Path to a compiler .jar file.
      pretty_print: True to pretty print the output.
      defines: A list of defines for conditional operators.
      compiler_flags: A list of string compiler flags.
      out: Optional output name. If none is provided than the rule name will be
          used.
    """
    super(ClosureGssRule, self).__init__(name, *args, **kwargs)
    self.mode = mode
    self.compiler_jar = compiler_jar
    self._append_dependent_paths([self.compiler_jar])
    self.pretty_print = pretty_print

    self.defines = []
    if defines:
      self.defines.extend(defines)

    self.compiler_flags = []
    if compiler_flags:
      self.compiler_flags.extend(compiler_flags)

    self.out = out

  class _Context(RuleContext):
    def begin(self):
      super(ClosureGssRule._Context, self).begin()

      args = []
      args.extend(self.rule.compiler_flags)

      needs_map_file = False
      if self.rule.mode == 'MINIFIED':
        args.extend(['--rename', 'NONE'])
      elif self.rule.mode == 'DEBUG_COMPILED':
        needs_map_file = True
        args.extend(['--rename', 'DEBUG'])
        args.extend(['--output-renaming-map-format', 'CLOSURE_COMPILED'])
      elif self.rule.mode == 'COMPILED':
        needs_map_file = True
        args.extend(['--rename', 'CLOSURE'])
        args.extend(['--output-renaming-map-format', 'CLOSURE_COMPILED'])

      if needs_map_file:
        map_path = self._get_gen_path(name=self.rule.out, suffix='.js')
        self._ensure_output_exists(os.path.dirname(map_path))
        self._append_output_paths([map_path])
        args.extend(['--output-renaming-map', map_path])

      if self.rule.pretty_print:
        args.append('--pretty-print')

      output_path = self._get_out_path(name=self.rule.out, suffix='.css')
      self._ensure_output_exists(os.path.dirname(output_path))
      self._append_output_paths([output_path])
      args.extend(['--output-file', output_path])

      args.extend(self.src_paths)

      jar_path = self._resolve_input_files([self.rule.compiler_jar])[0]
      d = self._run_task_async(JavaExecutableTask(
          self.build_env, jar_path, args))
      # TODO(benvanik): pull out (stdout, stderr) from result and the exception
      #     to get better error logging
      self._chain(d)
