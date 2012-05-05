# Copyright 2012 Google Inc. All Rights Reserved.

"""Closure compiler rules for the build system.

Contains the following rules:
closure_js_lint
closure_js_fixstyle
closure_js_library

Assumes Closure Linter is installed and on the path.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import io
import os
import re

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import (Task, ExecutableTask, JavaExecutableTask,
    WriteFileTask)
import anvil.util


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
    self.src_filter = '*.js'
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

      # TODO(benvanik): only changed paths
      args.extend(self.src_paths)

      d = self._run_task_async(ExecutableTask(
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


# TODO(benvanik): support non-closure code
# TODO(benvanik): support AMD modules
@build_rule('closure_js_library')
class ClosureJsLibraryRule(Rule):
  """A Closure compiler JavaScript library.
  Uses the Closure compiler to build a library from the given source files.

  Processes input files using the Closure compiler in the given mode.
  goog.provide and goog.require are used to order the files when concatenated.
  In SIMPLE and ADVANCED modes dependencies are used to remove dead code.

  If UNCOMPILED mode is used, only a -deps.js file is generated. This is a fast
  operation and can be used when interactively running code in a browser in
  uncompiled mode.

  A compiler JAR must be provided.

  Inputs:
    srcs: All source JS files.
    mode: Compilation mode, one of ['UNCOMPILED', 'SIMPLE', 'ADVANCED'].
    compiler_jar: Path to a compiler .jar file.
    entry_points: A list of entry points, such as 'myapp.start'.
    pretty_print: True to pretty print the output.
    debug: True to enable Closure DEBUG consts.
    compiler_flags: A list of string compiler flags.
    externs: Additional extern .js files.
    wrap_with_global: Wrap all output in a closure and call with the given
          global object.
          Example - 'global' -> (function(){...code...}).call(global);
    out: Optional output name. If none is provided than the rule name will be
        used.

  Outputs:
    A single compiled JS file. If no out is specified a file with the name of
    the rule will be created.
  """

  def __init__(self, name, mode, compiler_jar, entry_points,
        pretty_print=False, debug=False,
        compiler_flags=None, externs=None, wrap_with_global=None, out=None,
        *args, **kwargs):
    """Initializes a Closure JS library rule.

    Args:
      name: Rule name.
      mode: Compilation mode, one of ['UNCOMPILED', 'SIMPLE', 'ADVANCED'].
      compiler_jar: Path to a compiler .jar file.
      entry_points: A list of entry points, such as 'myapp.start'.
      pretty_print: True to pretty print the output.
      debug: True to enable Closure DEBUG consts.
      compiler_flags: A list of string compiler flags.
      externs: Additional extern .js files.
      wrap_with_global: Wrap all output in a closure and call with the given
          global object.
          Example - 'global' -> (function(){...code...}).call(global);
      out: Optional output name.
    """
    super(ClosureJsLibraryRule, self).__init__(name, *args, **kwargs)
    self.src_filter = '*.js'
    self.mode = mode
    self.compiler_jar = compiler_jar
    self._append_dependent_paths([self.compiler_jar])
    self.pretty_print = pretty_print
    self.debug = debug

    self.entry_points = []
    if isinstance(entry_points, str):
      self.entry_points.append(entry_points)
    elif entry_points:
      self.entry_points.extend(entry_points)

    self.compiler_flags = []
    if compiler_flags:
      self.compiler_flags.extend(compiler_flags)

    self.externs = []
    if externs:
      self.externs.extend(externs)
    self._append_dependent_paths(self.externs)

    self.wrap_with_global = wrap_with_global
    self.out = out

  class _Context(RuleContext):
    def begin(self):
      super(ClosureJsLibraryRule._Context, self).begin()

      jar_path = self._resolve_input_files([self.rule.compiler_jar])[0]
      args = [
          '--process_closure_primitives',
          '--generate_exports',
          '--summary_detail_level=3',
          '--warning_level=VERBOSE',
          ]
      args.extend(self.rule.compiler_flags)

      compiling = False
      if self.rule.mode == 'SIMPLE':
        compiling = True
        args.append('--compilation_level=SIMPLE_OPTIMIZATIONS')
      elif self.rule.mode == 'ADVANCED':
        compiling = True
        args.append('--compilation_level=ADVANCED_OPTIMIZATIONS')

      if self.rule.pretty_print:
        args.append('--formatting=PRETTY_PRINT')
        args.append('--formatting=PRINT_INPUT_DELIMITER')

      if not self.rule.debug:
        args.append('--define=goog.DEBUG=false')
        args.append('--define=goog.asserts.ENABLE_ASSERTS=false')

      if self.rule.wrap_with_global:
        args.append('--output_wrapper="(function(){%%output%%}).call(%s);"' % (
            self.rule.wrap_with_global))

      extern_paths = self._resolve_input_files(self.rule.externs)
      for extern_path in extern_paths:
        extern_flags.append('--externs=%s' % (extern_path))

      for entry_point in self.rule.entry_points:
        args.append('--closure_entry_point=%s' % (entry_point))

      if compiling:
        # Compiling - will generate the main js library
        output_path = self._get_out_path(name=self.rule.out, suffix='.js')
        self._ensure_output_exists(os.path.dirname(output_path))
        self._append_output_paths([output_path])
        args.append('--js_output_file=%s' % (output_path))
      else:
        # Uncompiled - will generate a deps.js file
        deps_js_path = self._get_out_path(name=self.rule.out, suffix='-deps.js')
        self._ensure_output_exists(os.path.dirname(deps_js_path))
        self._append_output_paths([deps_js_path])

      # Issue dependency scanning to build the deps graph
      d = self._run_task_async(_ScanJsDependenciesTask(
          self.build_env, self.src_paths))

      # Launch the compilation and deps.js gen tasks when scanning completes
      def _deps_scanned(dep_graph):
        ds = []

        # Grab all used files
        used_paths = dep_graph.get_transitive_closure(self.rule.entry_points)

        # Generate/write JS deps
        if not compiling:
          ds.append(self._run_task_async(WriteFileTask(
              self.build_env, dep_graph.get_deps_js(), deps_js_path)))

        # Compile main lib
        if compiling:
          for src_path in used_paths:
            args.append('--js=%s' % (src_path))
          ds.append(self._run_task_async(JavaExecutableTask(
              self.build_env, jar_path, args)))
          # TODO(benvanik): pull out (stdout, stderr) from result and the
          #     exception to get better error logging
        else:
          # Uncompiled - pass along all inputs as outputs
          self._append_output_paths(used_paths)

        self._chain(ds)

      # Kickoff chain
      d.add_callback_fn(_deps_scanned)
      self._chain_errback(d)


class _ScanJsDependenciesTask(Task):
  def __init__(self, build_env, src_paths, *args, **kwargs):
    super(_ScanJsDependenciesTask, self).__init__(build_env, *args, **kwargs)
    self.src_paths = src_paths

  def execute(self):
    deps_graph = JsDependencyGraph(self.build_env, self.src_paths)
    return deps_graph


class JsDependencyFile(object):
  """A single source JS file.
  Parses the file and finds all goog.provide and goog.require statements.
  """

  _PROVIDEREQURE_REGEX = re.compile(
      'goog\.(provide|require)\(\s*[\'"](.+)[\'"]\s*\)')
  _GOOG_BASE_LINE = (
      'var goog = goog || {}; // Identifies this file as the Closure base.\n')

  def __init__(self, src_path):
    """Initializes a JS dependency file.

    Args:
      src_path: Source JS file path.
    """
    self.src_path = src_path
    self.provides = []
    self.requires = []
    self.is_base_js = False
    self.is_css_rename_map = False
    with io.open(self.src_path, 'rt') as f:
      self._scan(f)

  def _scan(self, f):
    """Scans the given file for provides/requires and returns the results.

    Args:
      f: Input file.
    """
    provides = set()
    requires = set()

    for line in f.readlines():
      match = self._PROVIDEREQURE_REGEX.match(line)
      if match:
        if match.group(1) == 'provide':
          provides.add(str(match.group(2)))
        else:
          requires.add(str(match.group(2)))
      elif line == self._GOOG_BASE_LINE:
        provides.add('goog')
        self.is_base_js = True
      elif line.startswith('goog.setCssNameMapping('):
        self.is_css_rename_map = True

    self.provides = list(provides)
    self.provides.sort()
    self.requires = list(requires)
    self.requires.sort()


class JsDependencyGraph(object):
  """Represents a JS dependency graph.
  This scans all source JavaScript files to identify their dependencies.
  The result is a queryable list
  """

  def __init__(self, build_env, src_paths, *args, **kwargs):
    """Initializes a JS dependency graph.

    Args:
      build_env: BuildEnvironment.
      src_paths: A list of source JS paths.
    """
    self.build_env = build_env
    self.src_paths = list(src_paths)
    self.dep_files = {}
    self._provide_map = {}
    self.base_dep_file = None
    self.base_js_path = None

    # Scan all files
    for src_path in self.src_paths:
      dep_file = JsDependencyFile(src_path)
      self.dep_files[src_path] = dep_file
      if dep_file.is_base_js:
        self.base_dep_file = dep_file
        self.base_js_path = os.path.dirname(dep_file.src_path)
      for provide in dep_file.provides:
        assert not provide in self._provide_map
        self._provide_map[provide] = dep_file

  def get_deps_js(self):
    """Generates the contents of a deps.js file from the dependency graph.

    Returns:
      A string containing all of the lines of a deps.js file.
    """
    # Path that all dependencies will be relative from
    base_path = self.build_env.root_path
    if self.base_js_path:
      base_path = self.base_js_path

    lines = [
        '// Automatically generated by anvil-build - do not modify',
        '',
        ]

    # Write in path order (to make the file easier to debug)
    src_paths = self.dep_files.keys()
    src_paths.sort()
    for src_path in src_paths:
      dep_file = self.dep_files[src_path]
      rel_path = os.path.relpath(dep_file.src_path, base_path)
      rel_path = anvil.util.strip_build_paths(rel_path)
      lines.append('goog.addDependency(\'%s\', %s, %s);' % (
          rel_path, dep_file.provides, dep_file.requires))
    return u'\n'.join(lines)

  def get_transitive_closure(self, entry_points):
    """Identifies the transitive closure of the dependency graph for the given
    entry points.

    Args:
      entry_points: Closure entry points, such as 'my.start'.

    Returns:
      A list of all file paths required by the given entry points.
      The files are sorted in proper dependency order.
    """
    deps_list = []

    # Always base.js first
    if self.base_dep_file:
      deps_list.append(self.base_dep_file.src_path)

    # Followed by all files in the transitive closure, in order
    for entry_point in entry_points:
      self._add_dependencies(deps_list, entry_point)

    # And finally, any files that look special
    for dep_file in self.dep_files.values():
      if dep_file.is_css_rename_map:
        deps_list.append(dep_file.src_path)

    return deps_list

  def _add_dependencies(self, deps_list, namespace):
    if not namespace in self._provide_map:
      print 'Namespace %s not provided' % (namespace)
    assert namespace in self._provide_map
    dep_file = self._provide_map[namespace]
    if dep_file.src_path in deps_list:
      return
    for require in dep_file.requires:
      self._add_dependencies(deps_list, require)
    deps_list.append(dep_file.src_path)
