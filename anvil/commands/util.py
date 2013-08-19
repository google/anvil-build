# Copyright 2012 Google Inc. All Rights Reserved.

"""Common command utilities.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import shutil
import sys

from anvil.cache import RuleCache, FileRuleCache
from anvil.context import BuildEnvironment, BuildContext
from anvil.project import FileModuleResolver, Project
from anvil.task import InProcessTaskExecutor, MultiProcessTaskExecutor


def clean_output(cwd):
  """Cleans all build-related output and caches.

  Args:
    cwd: Current working directory.

  Returns:
    True if the clean succeeded.
  """
  nuke_paths = [
      '.build-cache',
      'build-out',
      'build-gen',
      'build-bin',
      ]
  any_failed = False
  for path in nuke_paths:
    full_path = os.path.join(cwd, path)
    if os.path.isdir(full_path):
      try:
        shutil.rmtree(full_path)
      except Exception as e:
        print('Unable to remove %s: %s' % (full_path, e))
        any_failed = True
  return not any_failed


def run_build(cwd, parsed_args):
  """Runs a build with the given arguments.
  Assumes that add_common_args and add_common_build_args was called on the
  ArgumentParser.

  Args:
    cwd: Current working directory.
    parsed_args: Argument namespace from an ArgumentParser.

  Returns:
    (success, a list of all target output paths)
  """
  if not len(parsed_args.targets):
    return (True, [])

  build_env = BuildEnvironment(root_path=cwd)

  module_resolver = FileModuleResolver(cwd)
  project = Project(module_resolver=module_resolver)

  # -j/--jobs switch to change execution mode
  #task_executor = None
  if parsed_args.jobs is None:
    # Default to -j1 on Windows only.
    # TODO(benvanik): figure out why this fails so catastrophically
    if (sys.platform == 'cygwin' or
        sys.platform == 'win32'):
      parsed_args.jobs = 1
  if parsed_args.jobs == 1:
    task_executor = InProcessTaskExecutor()
  else:
    task_executor = MultiProcessTaskExecutor(worker_count=parsed_args.jobs)

  # TODO(benvanik): good logging/info - resolve rules in project and print
  #     info?
  print('building %s' % (parsed_args.targets))

  # Setup cache
  if not parsed_args.force:
    cache_path = os.getcwd()
    rule_cache = FileRuleCache(cache_path)
  else:
    rule_cache = RuleCache()

  # TODO(benvanik): take additional args from command line
  all_target_outputs = set([])
  with BuildContext(build_env, project,
                    rule_cache=rule_cache,
                    task_executor=task_executor,
                    force=parsed_args.force,
                    stop_on_error=parsed_args.stop_on_error,
                    raise_on_error=False) as build_ctx:
    result = build_ctx.execute_sync(parsed_args.targets)
    if result:
      for target in parsed_args.targets:
        (state, target_outputs) = build_ctx.get_rule_results(target)
        all_target_outputs.update(target_outputs)

  return (result == True, all_target_outputs)
