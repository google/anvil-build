# Copyright 2012 Google Inc. All Rights Reserved.

"""Module representation.

A module is a simple namespace of rules, serving no purpose other than to allow
for easier organization of projects.

Rules may refer to other rules in the same module with a shorthand (':foo') or
rules in other modules by specifying a module-relative path
('stuff/other.py:bar').

TODO(benvanik): details on path resolution
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import ast
import glob2
import io
import os

import anvil.rule
from anvil.rule import RuleNamespace


class Module(object):
  """A rule module.
  Modules are a flat namespace of rules. The actual resolution of rules occurs
  later on and is done using all of the modules in a project, allowing for
  cycles/lazy evaluation/etc.
  """

  def __init__(self, path, rules=None):
    """Initializes a module.

    Args:
      path: A path for the module - should be the path on disk or some other
          string that is used for referencing.
      rules: A list of rules to add to the module.
    """
    self.path = path
    self.rules = {}
    if rules and len(rules):
      self.add_rules(rules)

  def add_rule(self, rule):
    """Adds a rule to the module.

    Args:
      rule: A rule to add. Must have a unique name.

    Raises:
      KeyError: A rule with the given name already exists in the module.
    """
    self.add_rules([rule])

  def add_rules(self, rules):
    """Adds a list of rules to the module.

    Args:
      rules: A list of rules to add. Each must have a unique name.

    Raises:
      KeyError: A rule with the given name already exists in the module.
    """
    for rule in rules:
      if self.rules.get(rule.name, None):
        raise KeyError('A rule with the name "%s" is already defined' % (
            rule.name))
    for rule in rules:
      self.rules[rule.name] = rule
      rule.set_parent_module(self)

  def get_rule(self, rule_name):
    """Gets a rule by name.

    Args:
      rule_name: Name of the rule to find. May include leading semicolon.

    Returns:
      The rule with the given name or None if it was not found.

    Raises:
      NameError: The given rule name was invalid.
    """
    print(rule_name)
    if rule_name or rule_name[0] == ':':
      rule_name = rule_name
    if not rule_name:
      raise NameError('Rule name "%s" is invalid' % (rule_name))
    return self.rules.get(rule_name, None)

  def rule_list(self):
    """Gets a list of all rules in the module.

    Returns:
      A list of all rules.
    """
    return self.rules.values()

  def rule_iter(self):
    """Iterates over all rules in the module."""
    for rule_name in self.rules:
      yield self.rules[rule_name]


class ModuleLoader(object):
  """A utility type that handles loading modules from files.
  A loader should only be used to load a single module and then be discarded.
  """

  def __init__(self, path, rule_namespace=None, modes=None):
    """Initializes a loader.

    Args:
      path: File-system path to the module.
      rule_namespace: Rule namespace to use for rule definitions.
    """
    self.path = path
    self.rule_namespace = rule_namespace
    if not self.rule_namespace:
      self.rule_namespace = RuleNamespace()
      self.rule_namespace.discover()
    self.modes = {}
    if modes:
      for mode in modes:
        if self.modes.has_key(mode):
          raise KeyError('Duplicate mode "%s" defined' % (mode))
        self.modes[mode] = True

    self.code_str = None
    self.code_ast = None
    self.code_obj = None

    self._current_scope = None

  def load(self, source_string=None):
    """Loads the module from the given path and prepares it for execution.

    Args:
      source_string: A string to use as the source. If not provided the file
          will be loaded at the initialized path.

    Raises:
      IOError: The file could not be loaded or read.
      SyntaxError: An error occurred parsing the module.
    """
    if self.code_str:
      raise Exception('ModuleLoader load called multiple times')

    # Read the source as a string
    if source_string is None:
      try:
        with io.open(self.path, 'r') as f:
          self.code_str = f.read()
      except Exception as e:
        raise IOError('Unable to find or read %s' % (self.path))
    else:
      self.code_str = source_string

    # Parse the AST
    # This will raise errors if it is not valid
    self.code_ast = ast.parse(self.code_str, self.path, 'exec')

    # Compile
    self.code_obj = compile(self.code_ast, self.path, 'exec')

  def execute(self):
    """Executes the module and returns a Module instance.

    Returns:
      A new Module instance with all of the rules.

    Raises:
      NameError: A function or variable name was not found.
    """
    all_rules = None
    anvil.rule.begin_capturing_emitted_rules()
    try:
      # Setup scope
      scope = {}
      self._current_scope = scope
      self.rule_namespace.populate_scope(scope)
      self._add_builtins(scope)

      # Execute!
      if self.code_obj in scope:
        exec(self.code_obj)
    finally:
      self._current_scope = None
      all_rules = anvil.rule.end_capturing_emitted_rules()

    # Gather rules and build the module
    module = Module(self.path)
    module.add_rules(all_rules)
    return module

  def _add_builtins(self, scope):
    """Adds builtin functions and types to a scope.

    Args:
      scope: Scope dictionary.
    """
    scope['glob'] = self.glob
    scope['include_rules'] = self.include_rules
    scope['select_one'] = self.select_one
    scope['select_any'] = self.select_any
    scope['select_many'] = self.select_many

  def glob(self, expr):
    """Globs the given expression with the base path of the module.
    This uses the glob2 module and supports recursive globs ('**/*').

    Args:
      expr: Glob expression.

    Returns:
      A list of all files that match the glob expression.
    """
    if not expr or not len(expr):
      return []
    base_path = os.path.dirname(self.path)
    glob_path = os.path.join(base_path, expr)
    return list(glob2.iglob(glob_path))

  def include_rules(self, srcs):
    """Scans the given paths for rules to include.
    Source strings must currently be file paths. Future versions may support
    referencing other rules.

    Args:
      srcs: A list of source strings or a single source string.
    """
    base_path = os.path.dirname(self.path)
    if isinstance(srcs, str):
      srcs = [srcs]
    for src in srcs:
      # TODO(benvanik): support references - requires making the module loader
      #     reentrant so that the referenced module can be loaded inline
      src = os.path.normpath(os.path.join(base_path, src))
      self.rule_namespace.discover_in_file(src)

    # Repopulate the scope so future statements pick up the new rules
    self.rule_namespace.populate_scope(self._current_scope)

  def select_one(self, d, default_value):
    """Selects a single value from the given tuple list based on the current
    mode settings.
    This is similar to select_any, only it ensures a reliable ordering in the
    case of multiple modes being matched.

    If 'A' and 'B' are two non-exclusive modes, then pass
    [('A', ...), ('B', ...)] to ensure ordering. If only A or B is defined then
    the respective values will be selected, and if both are defined then the
    last matching tuple will be returned - in the case of both A and B being
    defined, the value of 'B'.

    Args:
      d: A list of (key, value) tuples.
      default_value: The value to return if nothing matches.

    Returns:
      A value from the given dictionary based on the current mode, and if none
      match default_value.

    Raises:
      KeyError: Multiple keys were matched in the given dictionary.
    """
    value = None
    any_match = False
    for mode_tuple in d:
      if self.modes.has_key(mode_tuple[0]):
        any_match = True
        value = mode_tuple[1]
    if not any_match:
      return default_value
    return value

  def select_any(self, d, default_value):
    """Selects a single value from the given dictionary based on the current
    mode settings.
    If multiple keys match modes, then a random value will be returned.
    If you want to ensure consistent return behavior prefer select_one. This is
    only useful for exclusive modes (such as 'RELEASE' and 'DEBUG').

    For example, if 'DEBUG' and 'RELEASE' are exclusive modes, one can use a
    dictionary that has 'DEBUG' and 'RELEASE' as keys and if both DEBUG and
    RELEASE are defined as modes then a KeyError will be raised.

    Args:
      d: Dictionary of mode key-value pairs.
      default_value: The value to return if nothing matches.

    Returns:
      A value from the given dictionary based on the current mode, and if none
      match default_value.

    Raises:
      KeyError: Multiple keys were matched in the given dictionary.
    """
    value = None
    any_match = False
    for mode in d:
      if self.modes.has_key(mode):
        if any_match:
          raise KeyError(
              'Multiple modes match in the given dictionary - use select_one '
              'instead to ensure ordering')
        any_match = True
        value = d[mode]
    if not any_match:
      return default_value
    return value

  def select_many(self, d, default_value):
    """Selects as many values from the given dictionary as match the current
    mode settings.

    This expects the values of the keys in the dictionary to be uniform (for
    example, all lists, dictionaries, or primitives). If any do not match a
    TypeError is thrown.

    If values are dictionaries then the result will be a dictionary that is
    an aggregate of all matching values. If the values are lists then a single
    combined list is returned. All other types are placed into a list that is
    returned.

    Args:
      d: Dictionary of mode key-value pairs.
      default_value: The value to return if nothing matches.

    Returns:
      A list or dictionary of combined values that match any modes, or the
      default_value.

    Raises:
      TypeError: The type of a value does not match the expected type.
    """
    if isinstance(default_value, list):
      results = []
    elif isinstance(default_value, dict):
      results = {}
    else:
      results = []
    any_match = False
    for mode in d:
      if self.modes.has_key(mode):
        any_match = True
        mode_value = d[mode]
        if isinstance(mode_value, list):
          if type(mode_value) != type(default_value):
            raise TypeError('Type mismatch in dictionary (expected list)')
          results.extend(mode_value)
        elif isinstance(mode_value, dict):
          if type(mode_value) != type(default_value):
            raise TypeError('Type mismatch in dictionary (expected dict)')
          results.update(mode_value)
        else:
          if type(default_value) == list:
            raise TypeError('Type mismatch in dictionary (expected list)')
          elif type(default_value) == dict:
            raise TypeError('Type mismatch in dictionary (expected dict)')
          results.append(mode_value)
    if not any_match:
      if default_value is None:
        return None
      elif isinstance(default_value, list):
        results.extend(default_value)
      elif isinstance(default_value, dict):
        results.update(default_value)
      else:
        results.append(default_value)
    return results
