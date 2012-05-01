# Copyright 2012 Google Inc. All Rights Reserved.

"""Closure compiler rules for the build system.

Contains the following rules:
closure_js_lint
closure_js_fixstyle
closure_js_deps
closure_js_library

Assumes Closure Linter is installed and on the path.
Assumes Closure Library is present for deps.js generation.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task, JavaExecutableTask, PythonExecutableTask


@build_rule('closure_js_lint')
class ClosureJsLintRule(Rule):
  """A set of linted JS files.
  Passes all source files through the Closure style linter.

  Similar to file_set, all source files are globbed together and de-duplicated
  before being passed on as outputs. If a src_filter is provided then it is used
  to filter all sources.

  Inputs:
    srcs: Source JS file paths.
    namespaces: A list of Closurized namespaces.

  Outputs:
    All of the source file paths, passed-through unmodified.
  """

  def __init__(self, name, namespaces, *args, **kwargs):
    """Initializes a Closure JS lint rule.

    Args:
      name: Rule name.
      namespaces: A list of Closurized namespaces.
    """
    super(ClosureJsLintRule, self).__init__(name, *args, **kwargs)
    self._command = 'gjslint'
    self._extra_args = ['--nobeep',]
    self.namespaces = []
    self.namespaces.extend(namespaces)

  class _Context(RuleContext):
    def begin(self):
      super(ClosureJsLintRule._Context, self).begin()
      self._append_output_paths(self.src_paths)

      namespaces = ','.join(self.rule.namespaces)
      args = [
          '--strict',
          '--jslint_error=all',
          '--closurized_namespaces=%s' % (namespaces),
          ]

      d = self._run_task_async(PythonExecutableTask(
          self.build_env, self.rule._command, args))
      # TODO(benvanik): pull out errors?
      self._chain(d)


@build_rule('closure_js_fixstyle')
class ClosureJsFixStyleRule(ClosureJsLintRule):
  """A set of style-corrected JS files.
  Passes all source files through the Closure style fixer.

  Similar to file_set, all source files are globbed together and de-duplicated
  before being passed on as outputs. If a src_filter is provided then it is used
  to filter all sources.

  This rule is special in that it fixes the style of the source files in-place,
  overwriting them in their source path.

  Inputs:
    srcs: Source JS file paths.
    namespaces: A list of Closurized namespaces.

  Outputs:
    All of the source file paths, passed-through post-correction.
  """

  def __init__(self, name, namespaces, *args, **kwargs):
    """Initializes a Closure JS style fixing rule.

    Args:
      name: Rule name.
      namespaces: A list of Closurized namespaces.
    """
    super(ClosureJsFixStyleRule, self).__init__(name, namespaces,
        *args, **kwargs)
    self._command = 'fixjsstyle'
    self._extra_args = []


@build_rule('closure_js_deps')
class ClosureJsDepsRule(Rule):
  """A deps.js file for uncompiled Closure JS loading.
  Generates a deps.js file for the given sources containing dependency
  information. This file can be used to load the Closurized JS files in a
  browser without having to compile them first.

  Inputs:
    srcs: Source JS file paths.
    basejs_path: Path to the Closure base.js file.
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    A deps.js file for the given sources. If no out is specified a file with the
    name of the rule will be created.
  """

  def __init__(self, name, basejs_path, out=None, *args, **kwargs):
    """Initializes a Closure JS deps.js rule.

    Args:
      name: Rule name.
      basejs_path: Path to the Closure base.js file.
      out: Optional output name. If none is provided than the rule name will be
          used.
    """
    super(ClosureJsDepsRule, self).__init__(name, *args, **kwargs)
    self.basejs_path = basejs_path

  class _Context(RuleContext):
    def begin(self):
      super(ClosureJsDepsRule._Context, self).begin()

      # TODO(benvanik): implement
      self._succeed()

  """
  TODO(benvanik): implement deps.js generation
  This should work by loading all files source, finding all goog.require and
  goog.provide statements in them, and building a map of source path to
  (goog.provides, goog.requires).
  File should be written to the rule_name|out.
  Paths to the src files should be made relative to basejs_path.
  """


# TODO(benvanik): support non-closure code
# TODO(benvanik): support AMD modules
# TODO(benvanik): support sourcing the compiler JAR
@build_rule('closure_js_library')
class ClosureJsLibraryRule(Rule):
  """A Closure compiler JavaScript library.
  Uses the Closure compiler to build a library from the given source files.

  Processes input files using the Closure compiler in the given mode.
  goog.provide and goog.require are used to order the files when concatenated.
  In SIMPLE and ADVANCED modes dependencies are used to remove dead code.

  A compiler JAR must be provided.

  Inputs:
    srcs: All source JS files.
    mode: Compilation mode, one of ['SIMPLE', 'ADVANCED'].
    compiler_jar: Path to a compiler .jar file.
    entry_point: Entry point, such as 'myapp.start'.
    pretty_print: True to pretty print the output.
    debug: True to enable Closure DEBUG consts.
    compiler_flags: A list of string compiler flags.
    externs: Additional extern .js files.
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    A single compiled JS file. If no out is specified a file with the name of
    the rule will be created.
  """

  def __init__(self, name, mode, compiler_jar, entry_point,
        pretty_print=False, debug=False,
        compiler_flags=None, externs=None, out=None,
        *args, **kwargs):
    """Initializes a Closure JS library rule.

    Args:
      name: Rule name.
      mode: Compilation mode, one of ['SIMPLE', 'ADVANCED'].
      compiler_jar: Path to a compiler .jar file.
      entry_point: Entry point, such as 'myapp.start'.
      pretty_print: True to pretty print the output.
      debug: True to enable Closure DEBUG consts.
      compiler_flags: A list of string compiler flags.
      externs: Additional extern .js files.
      out: Optional output name.
    """
    super(ClosureJsLibraryRule, self).__init__(name, *args, **kwargs)
    self.mode = mode
    self.compiler_jar = compiler_jar
    self._append_dependent_paths([self.compiler_jar])
    self.entry_point = entry_point
    self.pretty_print = pretty_print
    self.debug = debug

    self.compiler_flags = []
    if compiler_flags:
      self.compiler_flags.extend(compiler_flags)

    self.externs = []
    if externs:
      self.externs.extend(externs)
    self._append_dependent_paths(self.externs)

    self.out = out

  class _Context(RuleContext):
    def begin(self):
      super(ClosureJsLibraryRule._Context, self).begin()

      args = [
          '--only_closure_dependencies',
          '--generate_exports',
          '--summary_detail_level=3',
          '--warning_level=VERBOSE',
          ]
      args.extend(self.rule.compiler_flags)

      args.append('--closure_entry_point=%s' % (self.rule.entry_point))

      if self.rule.mode == 'SIMPLE':
        args.append('--compilation_level=SIMPLE_OPTIMIZATIONS')
      elif self.rule.mode == 'ADVANCED':
        args.append('--compilation_level=ADVANCED_OPTIMIZATIONS')
      else:
        args.append('--compilation_level=WHITESPACE_ONLY')

      if self.rule.pretty_print:
        args.append('--formatting=PRETTY_PRINT')
        args.append('--formatting=PRINT_INPUT_DELIMITER')

      if not self.rule.debug:
        args.append('--define=goog.DEBUG=false')
        args.append('--define=goog.asserts.ENABLE_ASSERTS=false')

      output_path = self._get_out_path(name=self.rule.out, suffix='.js')
      self._ensure_output_exists(os.path.dirname(output_path))
      self._append_output_paths([output_path])
      args.append('--js_output_file=%s' % (output_path))

      extern_paths = self._resolve_input_files(self.rule.externs)
      for extern_path in extern_paths:
        extern_flags.append('--externs=%s' % (extern_path))

      for src_path in self.src_paths:
        args.append('--js=%s' % (src_path))

      jar_path = self._resolve_input_files([self.rule.compiler_jar])[0]
      d = self._run_task_async(JavaExecutableTask(
          self.build_env, jar_path, args))
      # TODO(benvanik): pull out (stdout, stderr) from result and the exception
      #     to get better error logging
      self._chain(d)


