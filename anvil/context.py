# Copyright 2012 Google Inc. All Rights Reserved.

"""Build context.

A build context is created to manage the dependency graph and build rules, as
well as handling distribution and execution of the tasks those rules create.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


from collections import deque
import fnmatch
import multiprocessing
import os
import stat

from anvil import async
from anvil.async import Deferred
from anvil import cache
from anvil import graph
from anvil import project
from anvil import task
from anvil import util


class Status:
  """Enumeration describing the status of a context."""
  WAITING = 0
  RUNNING = 1
  SUCCEEDED = 2
  FAILED = 3


class BuildEnvironment(object):
  """Build environment settings, containing access to all globals.
  Build environments are a combination of flags passed to the build system
  (from configuration files or the command line), system environment variables,
  and platform options.

  Rule and task implementations should avoid accessing the kind of information
  contained here from anywhere else (such as the sys module), as this ensures
  a consistent environment.

  The build environment should be kept constant throughout a build, and should
  be treated as read-only while in use by a context.

  This object may be passed to other processes, and must be pickeable.
  """

  def __init__(self, root_path=None):
    """Initializes a build environment.

    Args:
      root_path: Root path for base path resolution. If none is provided then
          the current working directory will be used.

    Raises:
      OSError: A path was not found or is wrong type.
    """
    # TODO(benvanik): cwd for path resolution
    # TODO(benvanik): environment variables
    # TODO(benvanik): user-defined options dict

    if not root_path or not len(root_path):
      self.root_path = os.getcwd()
    else:
      self.root_path = os.path.abspath(root_path)
    if not os.path.isdir(self.root_path):
      raise OSError('Root path "%s" not found or not a directory' % (
          self.root_path))


class BuildContext(object):
  """A build context for a given project and set of target rules.
  Projects are built by specifying rules that should be considered the
  'targets'. All rules that they depend on are then built, in the proper order,
  to ensure that all dependencies are up to date.

  Build contexts store the runtime definitions of rules, as well as the
  environment they run in.

  Build contexts are designed to be used once and thrown away. To start another
  build create a new context with the same parameters.
  """

  def __init__(self, build_env, project,
               rule_cache=None, task_executor=None, force=False,
               stop_on_error=False, raise_on_error=False):
    """Initializes a build context.

    Args:
      build_env: Current build environment.
      project: Project to use for building.
      rule_cache: Cache to use for rules.
      task_executor: Task executor to use. One will be created if none is
          passed.
      force: True to force execution of tasks even if they have not changed.
      stop_on_error: True to stop executing tasks as soon as an error occurs.
      raise_on_error: True to rethrow exceptions to ease debugging.
    """
    self.build_env = build_env
    self.project = project

    self.task_executor = task_executor
    self._close_task_executor = False
    if not self.task_executor:
      # HACK: multiprocessing on cygwin is really slow, so unless the caller
      # specifies we try to use the in-process executor to keep test times
      # low (any non-test callers should be specifying their own anyway)
      self.task_executor = task.InProcessTaskExecutor()
      #self.task_executor = task.MultiProcessTaskExecutor()
      self._close_task_executor = True

    self.force = force
    self.stop_on_error = stop_on_error
    self.raise_on_error = raise_on_error

    # Build the rule graph
    self.rule_graph = graph.RuleGraph(self.project)

    # Dictionary that should be used to map rule paths to RuleContexts
    self.rule_contexts = {}

    # Cache used to generate file deltas
    self.cache = rule_cache or cache.RuleCache()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    if self._close_task_executor:
      self.task_executor.close()

  def execute_sync(self, target_rule_names):
    """Synchronously executes the given target rules in the context.
    Rules are executed in the order and, where possible, in parallel.

    This is equivalent to calling execute_async and then waiting on the
    deferred.

    Args:
      target_rule_names: A list of rule names that are to be executed.

    Returns:
      A boolean indicating whether execution succeeded.

    Raises:
      KeyError: One of the given target rules was not found in the project.
      NameError: An invalid target rule was given.
      TypeError: An invalid target rule was given.
      RuntimeError: Execution failed to complete.
    """
    d = self.execute_async(target_rule_names)
    self.wait(d)
    result = [None]
    def _callback():
      result[0] = True
    def _errback():
      result[0] = False
    d.add_callback_fn(_callback)
    d.add_errback_fn(_errback)
    assert result[0] is not None
    return result[0]

  def execute_async(self, target_rule_names):
    """Executes the given target rules in the context.
    Rules are executed in the order and, where possible, in parallel.

    Args:
      target_rule_names: A list of rule names that are to be executed.

    Returns:
      A Deferred that completes when all rules have completed. If an error
      occurs in any rule an errback will be called.

    Raises:
      KeyError: One of the given target rules was not found in the project.
      NameError: An invalid target rule was given.
      TypeError: An invalid target rule was given.
    """
    # Verify that target rules are valid and exist
    target_rule_names = list(target_rule_names)
    util.validate_names(target_rule_names, require_semicolon=True)
    for rule_name in target_rule_names:
      if not self.project.resolve_rule(rule_name):
        raise KeyError('Target rule "%s" not found in project' % (rule_name))

    # Calculate the sequence of rules to execute
    rule_sequence = self.rule_graph.calculate_rule_sequence(target_rule_names)

    any_failed = [False]
    main_deferred = Deferred()
    remaining_rules = rule_sequence[:]
    in_flight_rules = []
    pumping = [False]

    def _issue_rule(rule):
      """Issues a single rule into the current execution context.
      Updates the in_flight_rules list and pumps when the rule completes.

      Args:
        rule: Rule to issue.
      """
      def _rule_callback(*args, **kwargs):
        in_flight_rules.remove(rule)
        _pump(previous_succeeded=True)

      def _rule_errback(exception=None, *args, **kwargs):
        in_flight_rules.remove(rule)
        # TODO(benvanik): log result/exception/etc?
        if exception: # pragma: no cover
          print(exception)
        any_failed[0] = True
        _pump(previous_succeeded=False)

      in_flight_rules.append(rule)
      rule_deferred = self._execute_rule(rule)
      rule_deferred.add_callback_fn(_rule_callback)
      rule_deferred.add_errback_fn(_rule_errback)
      return rule_deferred

    def _pump(previous_succeeded=True):
      """Attempts to run another rule and signals the main_deferred if done.

      Args:
        previous_succeeded: Whether the previous rule succeeded.
      """
      # If we're already done, gracefully exit
      if main_deferred.is_done():
        return

      # If we failed and we are supposed to stop, gracefully stop by
      # killing all future rules
      # This is better than terminating immediately, as it allows legit tasks
      # to finish
      if any_failed[0] and self.stop_on_error:
        remaining_rules[:] = []
        # TODO(benvanik): better error message
        main_deferred.errback()
        return

      if pumping[0]:
        return
      pumping[0] = True

      # Scan through all remaining rules - if any are unblocked, issue them
      to_issue = []
      for i in range(0, len(remaining_rules)):
        next_rule = remaining_rules[i]

        # Ignore if any dependency on any rule before it in the list
        skip_rule = False
        if i:
          for old_rule in remaining_rules[:i]:
            if self.rule_graph.has_dependency(next_rule.path, old_rule.path):
              # Blocked on previous rule
              skip_rule = True
              break
          if skip_rule:
            continue

        # Ignore if any dependency on an in-flight rule
        for in_flight_rule in in_flight_rules:
          if self.rule_graph.has_dependency(next_rule.path,
                                            in_flight_rule.path):
            # Blocked on a previous rule, so pass and wait for the next pump
            skip_rule = True
            break
        if skip_rule:
          continue

        # If here then we found no conflicting rules, queue for running
        to_issue.append(next_rule)

      # Run all rules that we can
      for rule in to_issue:
        remaining_rules.remove(rule)
      for rule in to_issue:
        _issue_rule(rule)

      if (not len(remaining_rules) and
          not len(in_flight_rules) and
          not main_deferred.is_done()):
        assert not len(remaining_rules)

        # Done!
        # TODO(benvanik): better errbacks? some kind of BuildResults?
        if not any_failed[0]:
          # Only save the cache when we have succeeded
          # This causes some stuff to be rebuilt in failure cases, but prevents
          # a lot of weirdness when things are partially broken
          self.cache.save()

          main_deferred.callback()
        else:
          main_deferred.errback()

      pumping[0] = False

      # Keep the queue pumping
      if not len(in_flight_rules) and len(remaining_rules):
        _pump()

    # Kick off execution (once for each rule as a heuristic for filling the
    # pipeline)
    for rule in rule_sequence:
      _pump()

    return main_deferred

  def wait(self, deferreds):
    """Blocks waiting on a list of deferreds until they all complete.
    The deferreds must have been returned from execute.

    Args:
      deferreds: A list of Deferreds (or one).
    """
    self.task_executor.wait(deferreds)

  def _execute_rule(self, rule):
    """Executes a single rule.
    This assumes that all dependent rules have already been executed. Assertions
    will be raised if all dependent rules have not completed successfully or
    if the given rule has been executed already.

    Args:
      rule: Rule to execute.

    Returns:
      A Deferred that will callback when the rule has completed executing.
    """
    assert not self.rule_contexts.has_key(rule.path)
    rule_ctx = rule.create_context(self)
    self.rule_contexts[rule.path] = rule_ctx
    if rule_ctx.check_predecessor_failures():
      return rule_ctx.cascade_failure()
    else:
      rule_ctx.begin()
      return rule_ctx.deferred

  def get_rule_results(self, rule):
    """Gets the status/output of a rule.
    This is not thread safe and should only be used to query the result of a
    rule after it has been run.

    Args:
      rule: Rule to query - can be a Rule object or a rule path that will be
          resolved.

    Returns:
      A tuple containing (status, output_paths) for the given rule.

    Raises:
      KeyError: The rule was not found.
    """
    if isinstance(rule, str):
      rule = self.project.resolve_rule(rule)
    if self.rule_contexts.has_key(rule.path):
      rule_ctx = self.rule_contexts[rule.path]
      return (rule_ctx.status, rule_ctx.all_output_files[:])
    else:
      return (Status.WAITING, [])

  def get_rule_outputs(self, rule):
    """Gets the output files of the given rule.
    It is only valid to call this on rules that have already been executed
    and have succeeded.

    Args:
      rule: Rule to query - can be a Rule object or a rule path that will be
          resolved.

    Returns:
      A list of all output files from the rule or None if the rule did not yet
      execute.
    Raises:
      KeyError: The rule was not found.
    """
    results = self.get_rule_results(rule)
    return results[1]


class RuleContext(object):
  """A runtime context for an individual rule.
  Must contain all of the state for a rule while it is being run, including
  all resolved inputs and resulting outputs (once complete).
  """

  def __init__(self, build_context, rule, *args, **kwargs):
    """Initializes a rule context.

    Args:
      build_context: BuildContext this rule is running in.
      rule: Rule this context wraps.
    """
    self.build_context = build_context
    self.build_env = build_context.build_env
    self.rule = rule

    self.file_delta = None

    self.deferred = Deferred()
    self.status = Status.WAITING
    self.start_time = None
    self.end_time = None
    self.exception = None

    # TODO(benvanik): logger
    self.logger = None

    # Resolve all src paths
    # If rules have their own attrs they'll have to do them themselves
    self.src_paths = self._resolve_input_files(rule.srcs, apply_src_filter=True)

    # This list of all files this rule outputted, upon completion
    self.all_output_files = []

  def _get_rule_path(self):
    """Gets the path to the directory containing the rule.

    Returns:
      Path to the directory that contains the module that this rule is in.
    """
    return os.path.dirname(self.rule.parent_module.path)

  def _resolve_input_files(self, paths, apply_src_filter=False):
    """Resolves the given paths into real file system paths, ready for use.
    This adds direct file references, recursively enumerates paths, expands
    globs, and grabs outputs from other rules.

    Since this actually checks to see if specific files are present and raises
    if not, this should be called in the initializer of all subclasses to
    resolve all paths in a place where a good stack will occur.

    Note that the resulting list is not deduplicated - certain rules may want
    the exact list in the exact order defined. If you want a de-duped list,
    simply use list(set(result)) to quickly de-dupe.

    Args:
      paths: Paths to resolve.

    Returns:
      A list of all file paths from the given paths.

    Raises:
      KeyError: A required rule was not found.
      OSError: A source path was not found or could not be accessed.
      RuntimeError: Internal runtime error (rule executed out of order/etc)
    """
    include_filter_list = []
    if apply_src_filter and self.rule.src_filter:
      include_filter_list = self.rule.src_filter.split('|')
    exclude_filter_list = []
    if apply_src_filter and self.rule.src_exclude_filter:
      exclude_filter_list = self.rule.src_exclude_filter.split('|')

    base_path = os.path.dirname(self.rule.parent_module.path)
    input_paths = []
    for src in paths:
      # Grab all items from the source
      src_items = None
      if util.is_rule_path(src):
        # Reference to another rule
        other_rule = self.build_context.project.resolve_rule(
            src, requesting_module=self.rule.parent_module)
        if not other_rule:
          raise KeyError('Source rule "%s" not found' % (src))
        if not self.build_context.rule_contexts.has_key(other_rule.path):
          raise RuntimeError('Source rule "%s" not yet executed' % (src))
        other_rule_ctx = self.build_context.rule_contexts[other_rule.path]
        src_items = other_rule_ctx.all_output_files
      else:
        # File or folder path
        src_path = os.path.join(base_path, src)
        if not os.path.exists(src_path):
          raise OSError('Source path "%s" not found' % (src_path))
        elif os.path.isdir(src_path):
          src_items = [os.path.join(src_path, child)
                       for child in os.listdir(src_path)]
        else:
          src_items = [src_path]

      # Apply the src_filter, if any
      if len(include_filter_list) or len(exclude_filter_list):
        for file_path in src_items:
          file_name = os.path.basename(file_path)
          if any(fnmatch.fnmatch(file_name, f) for f in exclude_filter_list):
            continue
          if (not len(include_filter_list) or
              any(fnmatch.fnmatch(file_name, f) for f in include_filter_list)):
            input_paths.append(file_path)
      else:
        input_paths.extend(src_items)
    return input_paths

  def __get_target_path(self, base_path, name=None, suffix=None):
    """Handling of _get_*_path() methods.

    Args:
      base_path: Base path to the project root.
      name: If a name is provided it will be used instead of the rule name.
      suffix: Suffix to add to whatever path is built, such as '.txt' to add
          an extension.

    Returns:
      A full path that can be used to write a file.
    """
    if not name or not len(name):
      name = self.rule.name
    if suffix and len(suffix):
      name += suffix
    root_path = self.build_context.build_env.root_path
    module_path = os.path.dirname(self.rule.parent_module.path)
    rel_path = os.path.relpath(module_path, root_path)
    return os.path.normpath(os.path.join(base_path, rel_path, name))

  def _get_root_path(self, name=None, suffix=None):
    """Gets the path of the given output in the root path.

    Always prefer _get_out_path and _get_gen_path.

    Args:
      name: If a name is provided it will be used instead of the rule name.
      suffix: Suffix to add to whatever path is built, such as '.txt' to add
          an extension.

    Returns:
      A full path that can be used to write a file to the proper root path.
    """
    base_path = self.build_context.build_env.root_path
    return self.__get_target_path(base_path, name=name, suffix=suffix)

  def _get_out_path(self, name=None, suffix=None):
    """Gets the 'out' path for an output.
    If no name is provided then the rule name will be used.

    The 'out' path should be used for all content/binary results.

    Args:
      name: If a name is provided it will be used instead of the rule name.
      suffix: Suffix to add to whatever path is built, such as '.txt' to add
          an extension.

    Returns:
      A full path that can be used to write a file to the proper 'out' path.
    """
    base_path = os.path.join(self.build_context.build_env.root_path,
                             'build-out')
    return self.__get_target_path(base_path, name=name, suffix=suffix)

  def _get_gen_path(self, name=None, suffix=None):
    """Gets the 'gen' path for an output.
    If no name is provided then the rule name will be used.

    The 'gen' path should be used for generated code only.

    Args:
      name: If a name is provided it will be used instead of the rule name.
      suffix: Suffix to add to whatever path is built, such as '.txt' to add
          an extension.

    Returns:
      A full path that can be used to write a file to the proper 'gen' path.
    """
    base_path = os.path.join(self.build_context.build_env.root_path,
                             'build-gen')
    return self.__get_target_path(base_path, name=name, suffix=suffix)

  def __get_target_path_for_src(self, base_path, src, opt_path=None):
    """Handling of _get_*_path_for_src() methods.

    Args:
      base_path: Base path to the project root.
      src: Absolute source path.

    Returns:
      A full path that can be used to write a file.
    """
    root_path = self.build_context.build_env.root_path
    rel_path = os.path.relpath(src, root_path)
    rel_path = util.strip_build_paths(rel_path)
    return os.path.normpath(os.path.join(base_path, rel_path))

  def _get_out_path_for_src(self, src):
    """Gets the 'out' path for a source file.

    The 'out' path should be used for all content/binary results.

    Args:
      src: Absolute source path.

    Returns:
      A full path that can be used to write a file to the proper 'out' path.
    """
    base_path = os.path.join(self.build_context.build_env.root_path,
                             'build-out')
    return self.__get_target_path_for_src(base_path, src)

  def _get_gen_path_for_src(self, src):
    """Gets the 'gen' path for a source file.

    The 'gen' path should be used for generated code only.

    Args:
      src: Absolute source path.

    Returns:
      A full path that can be used to write a file to the proper 'gen' path.
    """
    base_path = os.path.join(self.build_context.build_env.root_path,
                             'build-gen')
    return self.__get_target_path_for_src(base_path, src)

  def _ensure_output_exists(self, path):
    """Makes the given path exist, if it doesn't.

    Arg:
      path: An absolute path to a folder that should exist.
    """
    if not os.path.isdir(path):
      os.makedirs(path)

  def _append_output_paths(self, paths):
    """Appends the given paths to the output list.
    Other rules that depend on this rule will receive these paths when it
    is used as a source.

    Args:
      paths: A list of paths to add to the list.
    """
    self.all_output_files.extend(paths)

  def _run_task_async(self, task):
    """Runs a task asynchronously.
    This is a utility method that makes it easier to execute tasks.

    Args:
      task: Task to execute.

    Returns:
      A deferred that signals when the task completes.
    """
    return self.build_context.task_executor.run_task_async(task)

  def check_predecessor_failures(self):
    """Checks all dependencies for failure.

    Returns:
      True if any dependency has failed.
    """
    for dep in self.rule.get_dependent_paths():
      if util.is_rule_path(dep):
        other_rule = self.build_context.project.resolve_rule(
            dep, requesting_module=self.rule.parent_module)
        other_rule_ctx = self.build_context.rule_contexts.get(
            other_rule.path, None)
        if other_rule_ctx.status == Status.FAILED:
          return True
    return False

  def begin(self):
    """Begins asynchronous rule execution.
    Custom RuleContext implementations should override this method to perform
    their behavior (spawning tasks/etc). When the returned Deferred is called
    back the rule context should be completed, with all_output_files properly
    set.

    The default implementation ends immediately, passing all input files through
    as output.

    Returns:
      A Deferred that can will be called back when the rule has completed.
    """
    self.status = Status.RUNNING
    self.start_time = util.timer()

    # TODO(benvanik): real logging of rule processing
    # This makes the path relative and strips BUILD: (which may be wrong, w/e)
    rel_path = os.path.relpath(self.rule.path, self.build_env.root_path)
    rel_path = util.strip_implicit_build_name(rel_path)

    print('... %20s ~ %s' % (self.rule.rule_name, rel_path))

    # Compute file delta
    # Note that this could be done async (somehow)
    self.file_delta = self.build_context.cache.compute_delta(
        self.rule.path, 'src', self.src_paths)

    return self.deferred

  def _check_if_cached(self):
    """Checks if all inputs and outputs match their expected values.

    Returns:
      True if no inputs or outputs have changed.
    """
    # If any input changed...
    if self.file_delta.any_changes():
      return False

    # If any output was removed...
    output_delta = self.build_context.cache.compute_delta(
        self.rule.path, 'out', self.all_output_files)
    if len(output_delta.removed_files):
      return False

    return True

  def cascade_failure(self):
    """Instantly fails a rule, signaling that a rule prior to it has failed
    and it should not be run.

    Use this if a call to check_predecessor_failures returns True to properly
    set a rule context up for cascading failures.
    After calling this begin should not be called.

    Returns:
      A Deferred that has had its errback called.
    """
    # TODO(benvanik): special CascadingError exception
    self.start_time = util.timer()
    self._fail()
    return self.deferred

  def _succeed(self):
    """Signals that rule execution has completed successfully.
    This will set all state and issue the callback on the deferred.
    """
    self.status = Status.SUCCEEDED
    self.end_time = util.timer()
    self.deferred.callback()

  def _fail(self, exception=None, *args, **kwargs):
    """Signals that rule execution has completed in failure.
    This will set all state and issue the errback on the deferred.
    If an exception is provided it will be set on the context and passed as
    the first argument to the deferred.

    Args:
      exception: The exception that resulted in the rule failure, if any.
    """
    self.status = Status.FAILED
    self.end_time = util.timer()
    self.exception = exception
    # TODO(benvanik): real logging of rule failure
    print('!! failed %s' % (self.rule))
    if exception:
      self.deferred.errback(exception=exception)
    else:
      self.deferred.errback()

  def _chain(self, deferreds):
    """Chains the completion of the rule on the given deferred.
    Depending on the success or failure the deferred, the rule context will
    succeeed or fail.

    Args:
      deferreds: A Deferred or list of deferreds that will be called back.
    """
    deferred = async.gather_deferreds(deferreds, errback_if_any_fail=True)
    def _callback(*args, **kwargs):
      self._succeed()
    deferred.add_callback_fn(_callback)
    self._chain_errback(deferred)

  def _chain_errback(self, deferred):
    """Chains an errback of a deferred to the failure of the rule.

    Args:
      deferred: A Deferred to listen for.
    """
    def _errback(*args, **kwargs):
      exception = None
      if len(args):
        for arg in args[0]:
          if not arg[0]:
            if len(arg[1]) and isinstance(arg[1][0], Exception):
              exception = arg[1][0]
              break
            exception = arg[2].get('exception', None)
            if exception:
              break
      self._fail(exception=exception)
    deferred.add_errback_fn(_errback)
