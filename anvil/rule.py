# Copyright 2012 Google Inc. All Rights Reserved.

"""A single rule metadata blob.
Rules are defined by special rule functions (found under anvil.rules). They are
meant to be immutable and reusable, and contain no state.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import base64
import fnmatch
import hashlib
import imp
import os
import pickle
import re
import sys

from anvil import util
from anvil import version


class Rule(object):
  """A rule definition.
  Rules are the base unit in a module and can depend on other rules via either
  source (which depends on the outputs of the rule) or explicit dependencies
  (which just requires that the other rule have been run before).

  Sources can also refer to files, folders, or file globs. When a rule goes to
  run a list of sources will be compiled from the outputs from the previous
  rules as well as all real files on the file system.

  Rules must define a _Context class that extends RuleContext. This context
  will be used when executing the rule to store any temporary state and
  execution progress. Rules should not be modified after their initial
  construction, and instead the _Context should be used.
  """

  _whitespace_re = re.compile('\s', re.M)

  def __init__(self, name, srcs=None, deps=None, src_filter=None,
               src_exclude_filter=None, rule_name=None, *args, **kwargs):
    """Initializes a rule.

    Args:
      name: A name for the rule - should be literal-like and contain no leading
          or trailing whitespace.
      srcs: A list of source strings or a single source string.
      deps: A list of depdendency strings or a single dependency string.
      src_filter: An inclusionary file name filter for all non-rule paths. If
          defined only srcs that match this filter will be included.
      src_exclude_filter: An exclusionary file name filter for all non-rule
          paths. If defined only srcs that do not match this filter will be
          included.
      rule_name: Name of the rule in BUILD files, making it easier to debug.

    Raises:
      NameError: The given name is invalid (None/0-length).
      TypeError: The type of an argument or value is invalid.
    """
    if not name or not len(name):
      raise NameError('Invalid name')
    if self._whitespace_re.search(name):
      raise NameError('Name contains leading or trailing whitespace')
    if name[0] == ':':
      raise NameError('Name cannot start with :')
    self.name = name

    # For debugging
    self.rule_name = rule_name if rule_name else 'rule?'

    # Path will be updated when the parent module is set
    self.parent_module = None
    self.path = ':%s' % (name)

    # All file/rule paths this rule depends on - as a set so no duplicates
    self._dependent_paths = set([])

    self.srcs = []
    if isinstance(srcs, str):
      if len(srcs):
        self.srcs.append(srcs)
    elif isinstance(srcs, list):
      self.srcs.extend(srcs)
    elif srcs != None:
      raise TypeError('Invalid srcs type')
    self._append_dependent_paths(self.srcs)

    self.deps = []
    if isinstance(deps, str):
      if len(deps):
        self.deps.append(deps)
    elif isinstance(deps, list):
      self.deps.extend(deps)
    elif deps != None:
      raise TypeError('Invalid deps type')
    self._append_dependent_paths(self.deps, require_semicolon=True)

    self.src_filter = None
    if src_filter and len(src_filter):
      self.src_filter = src_filter
    self.src_exclude_filter = None
    if src_exclude_filter and len(src_exclude_filter):
      self.src_exclude_filter = src_exclude_filter

  def __repr__(self):
    return '%s(%s)' % (self.rule_name, self.path)

  def _append_dependent_paths(self, paths, require_semicolon=False):
    """Appends a list of paths to the rule's dependent paths.
    A dependent path is a file/rule that is required for execution and, if
    changed, will invalidate cached versions of this rule.

    Args:
      paths: A list of paths to depend on.
      require_semicolon: True if all of the given paths require a semicolon
          (so they must be rules).

    Raises:
      NameError: One of the given paths is invalid.
    """
    util.validate_names(paths, require_semicolon=require_semicolon)
    self._dependent_paths.update(paths)

  def get_dependent_paths(self):
    """Gets a list of all dependent paths.
    Paths may be file paths or rule paths.

    Returns:
      A list of file/rule paths.
    """
    return self._dependent_paths.copy()

  def set_parent_module(self, module):
    """Sets the parent module of a rule.
    This can only be called once.

    Args:
      module: New parent module for the rule.

    Raises:
      ValueError: The parent module has already been set.
    """
    if self.parent_module:
      raise ValueError('Rule "%s" already has a parent module' % (self.name))
    self.parent_module = module
    self.path = '%s:%s' % (module.path, self.name)

  def compute_cache_key(self):
    """Calculates a unique key based on the rule type and its values.
    This key may change when code changes, but is a fairly reliable way to
    detect changes in rule values.

    Returns:
      A string that can be used to index this key in a dictionary. The string
      may be very long.
    """
    # TODO(benvanik): faster serialization than pickle?
    pickled_self = pickle.dumps(self)
    pickled_str = base64.b64encode(pickled_self)
    # Include framework version in the string to enable forced rebuilds on
    # version change
    unique_str = version.VERSION_STR + pickled_str
    # Hash so that we return a reasonably-sized string
    return hashlib.md5(unique_str).hexdigest()

  def create_context(self, build_context):
    """Creates a new RuleContext that is used to run the rule.
    Rule implementations should return their own RuleContext type that
    has custom behavior.

    Args:
      build_context: The current BuildContext that should be passed to the
          RuleContext.

    Returns:
      A new RuleContext.
    """
    assert self._Context
    return self._Context(build_context, self)


# Active rule namespace that is capturing all new rule definitions
# This should only be modified by RuleNamespace.discover
_RULE_NAMESPACE = None

class RuleNamespace(object):
  """A namespace of rule type definitions and discovery services.
  """

  def __init__(self):
    """Initializes a rule namespace."""
    self.rule_types = {}
    self._loaded_files = []

  def populate_scope(self, scope):
    """Populates the given scope dictionary with all of the rule types.

    Args:
      scope: Scope dictionary.
    """
    for rule_name in self.rule_types:
      scope[rule_name] = self.rule_types[rule_name]

  def add_rule_type(self, rule_name, rule_cls):
    """Adds a rule type to the namespace.

    Args:
      rule_name: The name of the rule type exposed to modules.
      rule_cls: Rule type class.
    """
    def rule_definition(name, *args, **kwargs):
      rule = rule_cls(name, rule_name=rule_name, *args, **kwargs)
      _emit_rule(rule)
    rule_definition.rule_name = rule_name
    if self.rule_types.has_key(rule_name):
      raise KeyError('Rule type "%s" already defined' % (rule_name))
    self.rule_types[rule_name] = rule_definition

  def add_rule_type_fn(self, rule_type):
    """Adds a rule type to the namespace.
    This assumes the type is a function that is setup to emit the rule.
    It should only be used by internal methods.

    Args:
      rule_type: Rule type.
    """
    rule_name = rule_type.rule_name
    if rule_name in self.rule_types:
      raise KeyError('Rule type "%s" already defined' % (rule_name))
    self.rule_types[rule_name] = rule_type

  def discover(self, path=None):
    """Recursively searches the given path for rule type definitions.
    Files are searched with the pattern '*_rules.py' for types decorated with
    @build_rule.

    Each module is imported as discovered into the python module list and will
    be retained. Calling this multiple times with the same path has no effect.

    Args:
      path: Path to search for rule type modules. If omitted then the built-in
          rule path will be searched instead. If the path points to a file it
          will be checked, even if it does not match the name rules.
    """
    original_rule_types = self.rule_types.copy()
    try:
      if not path:
        path = os.path.join(os.path.dirname(__file__), 'rules')
      if os.path.isfile(path):
        self.discover_in_file(path)
      else:
        for (dirpath, dirnames, filenames) in os.walk(path):
          for filename in filenames:
            if fnmatch.fnmatch(filename, '*_rules.py'):
              self.discover_in_file(os.path.join(dirpath, filename))
    except:
      # Restore original types (don't take any of the discovered rules)
      self.rule_types = original_rule_types
      raise

  def discover_in_file(self, path):
    """Loads the given python file to add all of its rules.

    Args:
      path: Python file path.
    """
    if path in self._loaded_files:
      return

    global _RULE_NAMESPACE
    assert _RULE_NAMESPACE is None
    _RULE_NAMESPACE = self
    try:
      name = os.path.splitext(os.path.basename(path))[0]
      module = imp.load_source(name, path)
    finally:
      _RULE_NAMESPACE = None

    self._loaded_files.append(path)


# Used by begin_capturing_emitted_rules/build_rule to track all emitted rules
_EMIT_RULE_SCOPE = None

def begin_capturing_emitted_rules():
  """Begins capturing all rules emitted by @build_rule.
  Use end_capturing_emitted_rules to end capturing and return the list of rules.
  """
  global _EMIT_RULE_SCOPE
  assert not _EMIT_RULE_SCOPE
  _EMIT_RULE_SCOPE = []

def end_capturing_emitted_rules():
  """Ends a rule capture and returns any rules emitted.

  Returns:
    A list of rules that were emitted by @build_rule.
  """
  global _EMIT_RULE_SCOPE
  assert _EMIT_RULE_SCOPE is not None
  rules = _EMIT_RULE_SCOPE
  _EMIT_RULE_SCOPE = None
  return rules

def _emit_rule(rule):
  """Emits a rule.
  This should only ever be called while capturing.

  Args:
    rule: Rule that is being emitted.
  """
  global _EMIT_RULE_SCOPE
  assert _EMIT_RULE_SCOPE is not None
  _EMIT_RULE_SCOPE.append(rule)


class build_rule(object):
  """A decorator for build rule classes.
  Use this to register build rule classes. A class decorated with this will be
  exposed to modules with the given rule_name. It should be callable and, on
  call, use emit_rule to emit a new rule.
  """

  def __init__(self, rule_name):
    """Initializes the build rule decorator.

    Args:
      rule_name: The name of the rule type exposed to modules.
    """
    self.rule_name = rule_name

  def __call__(self, cls):
    # This wrapper function makes it possible to record all invocations of
    # a rule while loading the module
    rule_name = self.rule_name
    def rule_definition(name, *args, **kwargs):
      rule = cls(name, rule_name=rule_name, *args, **kwargs)
      _emit_rule(rule)
    rule_definition.rule_name = self.rule_name

    # Add the (wrapped) rule type to the global namespace
    # We support not having an active namespace so that tests can import
    # rule files without dying
    global _RULE_NAMESPACE
    if _RULE_NAMESPACE:
      _RULE_NAMESPACE.add_rule_type_fn(rule_definition)
    return cls
