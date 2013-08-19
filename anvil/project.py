# Copyright 2012 Google Inc. All Rights Reserved.

"""Project representation.

A project is a module (or set of modules) that provides a namespace of rules.
Rules may refer to each other and will be resolved in the project namespace.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import base64
import os
import pickle
import re
import stat
import string

from anvil.module import ModuleLoader
from anvil.rule import RuleNamespace
import anvil.util


class Project(object):
  """Project type that contains rules.
  Projects, once constructed, are designed to be immutable. Many duplicate
  build processes may run over the same project instance and all expect it to
  be in the state it was when first created.
  """

  def __init__(self, name='Project', rule_namespace=None, module_resolver=None,
               modules=None):
    """Initializes an empty project.

    Args:
      name: A human-readable name for the project that will be used for
          logging.
      rule_namespace: Rule namespace to use when loading modules. If omitted a
          default one is used.
      module_resolver: A module resolver to use when attempt to dynamically
          resolve modules by path.
      modules: A list of modules to add to the project.

    Raises:
      NameError: The name given is not valid.
    """
    self.name = name

    if rule_namespace:
      self.rule_namespace = rule_namespace
    else:
      self.rule_namespace = RuleNamespace()
      self.rule_namespace.discover()

    if module_resolver:
      self.module_resolver = module_resolver
    else:
      self.module_resolver = StaticModuleResolver()

    self.modules = {}
    if modules and len(modules):
      self.add_modules(modules)

  def add_module(self, module):
    """Adds a module to the project.

    Args:
      module: A module to add.

    Raises:
      KeyError: A module with the given name already exists in the project.
    """
    self.add_modules([module])

  def add_modules(self, modules):
    """Adds a list of modules to the project.

    Args:
      modules: A list of modules to add.

    Raises:
      KeyError: A module with the given name already exists in the project.
    """
    for module in modules:
      if self.modules.get(module.path, None):
        raise KeyError('A module with the path "%s" is already defined' % (
            module.path))
    for module in modules:
      self.modules[module.path] = module

  def get_module(self, module_path):
    """Gets a module by path.

    Args:
      module_path: Name of the module to find.

    Returns:
      The module with the given path or None if it was not found.
    """
    return self.modules.get(module_path, None)

  def module_list(self):
    """Gets a list of all modules in the project.

    Returns:
      A list of all modules.
    """
    return self.modules.values()

  def module_iter(self):
    """Iterates over all modules in the project."""
    for module_path in self.modules:
      yield self.modules[module_path]

  def resolve_rule(self, rule_path, requesting_module=None):
    """Gets a rule by path, supporting module lookup and dynamic loading.

    Args:
      rule_path: Path of the rule to find. Must include a semicolon.
      requesting_module: The module that is requesting the given rule. If not
          provided then no local rule paths (':foo') or relative paths are
          allowed.

    Returns:
      The rule with the given name or None if it was not found.

    Raises:
      NameError: The given rule name was not valid.
      KeyError: The given rule was not found.
      IOError: Unable to load referenced module.
    """
    if not anvil.util.is_rule_path(rule_path):
      raise NameError('The rule path "%s" is missing a semicolon' % (rule_path))
    (module_path, rule_name) = rule_path.split(':')
    print(rule_name)
    if self.module_resolver.can_resolve_local:
      if not len(module_path) and not requesting_module:
        module_path = '.'
    if not len(module_path) and not requesting_module:
      raise KeyError('Local rule "%s" given when no resolver defined' % (
          rule_path))

    module = requesting_module
    if len(module_path):
      requesting_path = None
      if requesting_module:
        requesting_path = os.path.dirname(requesting_module.path)
      full_path = self.module_resolver.resolve_module_path(
          module_path, requesting_path)
      module = self.modules.get(full_path, None)
      if not module:
        # Module not yet loaded - need to grab it
        module = self.module_resolver.load_module(
            full_path, self.rule_namespace)
        if module:
          self.add_module(module)
        else:
          raise IOError('Module "%s" not found', module_path)

    return module.get_rule(rule_name)


class ModuleResolver(object):
  """A type to use for resolving modules.
  This is used to get a module when a project tries to resolve a rule in a
  module that has not yet been loaded.
  """

  def __init__(self, *args, **kwargs):
    """Initializes a module resolver."""
    self.can_resolve_local = False

  def resolve_module_path(self, path, working_path=None):
    """Resolves a module path to its full, absolute path.
    This is used by the project system to disambugate modules and check the
    cache before actually performing a load.
    The path returned from this will be passed to load_module.

    Args:
      path: Path of the module (may be relative/etc).
      working_path: Path relative paths should be pased off of. If not provided
          then relative paths may fail.

    Returns:
      An absolute path that can be used as a cache key and passed to
      load_module.
    """
    raise NotImplementedError()

  def load_module(self, full_path, rule_namespace):
    """Loads a module from the given path.

    Args:
      full_path: Absolute path of the module as returned by resolve_module_path.
      rule_namespace: Rule namespace to use when loading modules.

    Returns:
      A Module representing the given path or None if it could not be found.

    Raises:
      IOError: The module could not be found.
    """
    raise NotImplementedError()


class StaticModuleResolver(ModuleResolver):
  """A static module resolver that can resolve from a list of modules.
  """

  def __init__(self, modules=None, *args, **kwargs):
    """Initializes a static module resolver.

    Args:
      modules: A list of modules that can be resolved.
    """
    super(StaticModuleResolver, self).__init__(*args, **kwargs)

    self.modules = {}
    if modules:
      for module in modules:
        self.modules[os.path.normpath(module.path)] = module

  def resolve_module_path(self, path, working_path=None):
    real_path = path
    if working_path and len(working_path):
      real_path = os.path.join(working_path, path)
    return os.path.normpath(real_path)

  def load_module(self, full_path, rule_namespace):
    return self.modules.get(os.path.normpath(full_path), None)


class FileModuleResolver(ModuleResolver):
  """A file-system backed module resolver.

  Rules are searched for with relative paths from a defined root path.
  If the module path given is a directory, the resolver will attempt to load
  a BUILD file from that directory - otherwise the file specified will be
  treated as the module.
  """

  def __init__(self, root_path, *args, **kwargs):
    """Initializes a file-system module resolver.

    Args:
      root_path: Root filesystem path to treat as the base for all resolutions.

    Raises:
      IOError: The given root path is not found or is not a directory.
    """
    super(FileModuleResolver, self).__init__(*args, **kwargs)

    self.can_resolve_local = True

    self.root_path = os.path.normpath(root_path)
    if not os.path.isdir(self.root_path):
      raise IOError('Root path "%s" not found' % (self.root_path))

  def resolve_module_path(self, path, working_path=None):
    # Compute the real path
    has_working_path = working_path and len(working_path)
    real_path = path
    if has_working_path:
      real_path = os.path.join(working_path, path)
    real_path = os.path.normpath(real_path)
    full_path = os.path.join(self.root_path, real_path)
    full_path = os.path.normpath(full_path)

    # Check to see if it exists and is a file
    # Special handling to find BUILD files under directories
    full_path = anvil.util.get_build_file_path(full_path)
    if not os.path.isfile(full_path):
      raise IOError('Path "%s" is not a file' % (full_path))

    return os.path.normpath(full_path)

  def load_module(self, full_path, rule_namespace):
    module_loader = ModuleLoader(full_path, rule_namespace=rule_namespace)
    module_loader.load()
    return module_loader.execute()
