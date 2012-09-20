# Copyright 2012 Google Inc. All Rights Reserved.

"""Closure template rules for the build system.

Contains the following rules:
closure_soy_library
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os

from anvil.context import RuleContext
from anvil.rule import Rule, build_rule
from anvil.task import Task, JavaExecutableTask


@build_rule('closure_soy_library')
class ClosureSoyLibraryRule(Rule):
  """A Closure Templates transformed file.
  Uses the Closure Templates compiler to translate input soy templates into
  JS files. Each input .soy file results in a single output .js file.

  Inputs:
    srcs: All source soy files.
    compiler_jar: Path to a compiler .jar file.
    compiler_flags: A list of string compiler flags.

  Outputs:
    One .js file for each input .soy file.
  """

  def __init__(self, name, compiler_jar, compiler_flags=None,
      *args, **kwargs):
    """Initializes a Closure templating rule.

    Args:
      srcs: All source soy files.
      compiler_jar: Path to a compiler .jar file.
      compiler_flags: A list of string compiler flags.
    """
    super(ClosureSoyLibraryRule, self).__init__(name, *args, **kwargs)
    self.compiler_jar = compiler_jar
    self._append_dependent_paths([self.compiler_jar])

    self.compiler_flags = []
    if compiler_flags:
      self.compiler_flags.extend(compiler_flags)

  class _Context(RuleContext):
    def begin(self):
      super(ClosureSoyLibraryRule._Context, self).begin()

      # If there are no source paths, die
      if not len(self.src_paths):
        self._succeed()
        return

      args = [
          '--shouldProvideRequireSoyNamespaces',
          '--shouldGenerateJsdoc',
          '--shouldGenerateGoogMsgDefs',
          '--bidiGlobalDir', '1',
          '--codeStyle', 'stringbuilder',
          '--cssHandlingScheme', 'goog',
          '--outputPathFormat', os.path.join(
              os.path.dirname(self._get_gen_path()),
              '{INPUT_DIRECTORY}/{INPUT_FILE_NAME_NO_EXT}-soy.js'),
          ]
      args.extend(self.rule.compiler_flags)

      for src_path in self.src_paths:
        output_path = os.path.splitext(self._get_gen_path_for_src(src_path))[0]
        output_path += '-soy.js'
        self._ensure_output_exists(os.path.dirname(output_path))
        self._append_output_paths([output_path])
        rel_path = os.path.relpath(src_path, self.build_env.root_path)
        args.append(rel_path)

      # Skip if cache hit
      if self._check_if_cached():
        self._succeed()
        return

      jar_path = self._resolve_input_files([self.rule.compiler_jar])[0]
      d = self._run_task_async(JavaExecutableTask(
          self.build_env, jar_path, args))
      # TODO(benvanik): pull out (stdout, stderr) from result and the exception
      #     to get better error logging
      self._chain(d)
