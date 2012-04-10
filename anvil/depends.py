# Copyright 2012 Google Inc. All Rights Reserved.

"""Dependency definition and management utilities.
Rules can define system dependencies such as libraries or applications that
are required to run them. The build system can then use this metadata to alert
the user to missing dependencies or help install them.
"""

# TODO(benvanik): refactor to allow install(deps) batches
# TODO(benvanik): refactor to make requirements tuples like:
#     ('node-module', 'glsl-unit@1.0.0')
#     ('python-package', 'argparse>=1.0')
#     (['apt-get', 'port'], 'foo')
#     ('brew', 'foo_lib', '1.0')

__author__ = 'benvanik@google.com (Ben Vanik)'


import pip
import pkg_resources
import os
import subprocess
import sys

from anvil.context import BuildEnvironment, BuildContext
from anvil.project import FileModuleResolver, Project
from anvil.task import InProcessTaskExecutor

class Dependency(object):
  """A dependency definition of an external library or application.
  Dependency definitions contain enough metadata for the build system to display
  meaningful and actionable error messages in the event of a missing dependency,
  as well as provide automatic installation support.
  """

  def __init__(self, *args, **kwargs):
    """Initializes a dependency definition.
    """
    self.requires_root = False

  def check(self):
    """Checks to see if the dependency is met.

    Returns:
      True if the dependency is valid and up to date. If the check could not be
      performed then None will be returned, signaling that an install is likely
      required.
    """
    raise NotImplementedError()

  def install(self):
    """Installs the dependency if it is not present.

    Returns:
      True if the installation completed successfully.
    """
    raise NotImplementedError()


class NodeLibrary(Dependency):
  """A dependency on a Node.js library.
  This will attempt to use npm to install the library locally.
  """

  def __init__(self, package_str, *args, **kwargs):
    """Initializes a Node.js library dependency definition.

    Args:
      package_str: Package string, such as 'some-lib@1.0' or a URL.
          This is passed directly to npm.
    """
    super(NodeLibrary, self).__init__(*args, **kwargs)
    self.package_str = package_str

  def check(self):
    # TODO(benvanik): find a way to check with NPM?
    # Could invoke node -e 'require("%s")'? would need the name to use
    return None

  def install(self):
    return subprocess.call(['npm', 'install', self.package_str]) == 0


class PythonLibrary(Dependency):
  """A dependency on a Python library.
  This uses pip to query the available libraries and install new ones.
  """

  def __init__(self, requirement_str, *args, **kwargs):
    """Initializes a Python library dependency definition.

    Args:
      requirement_str: Requirement string, such as 'anvil-build>=0.0.1'.
          This is passed directly to pip, so it supports extras and other
          features of requirement strings.
    """
    super(PythonLibrary, self).__init__(*args, **kwargs)
    self.requires_root = True
    self.requirement_str = requirement_str
    self.requirement = pkg_resources.Requirement.parse(requirement_str)

  def __str__(self):
    return 'Python Library "%s"' % (self.requirement_str)

  def check(self):
    any_found = False
    any_valid = False
    for distro in pip.get_installed_distributions():
      # distro is a pkg_resources.Distribution
      if distro in self.requirement:
        # Found and valid!
        any_found = True
        any_valid = True
      elif distro.project_name == self.requirement.project_name:
        # Present, but old
        any_found = True
        any_valid = False
    # TODO(benvanik): something with the result? log? different values?
    return any_found and any_valid

  def install(self):
    return pip.main(['install', self.requirement_str]) == 0


class NativePackage(Dependency):
  """A dependency on a native system package.
  This will attempt to use a supported platform package manager such as MacPorts
  or apt-get to install a dependency. If that fails it can (if supported) try
  to build from source.
  """

  def __init__(self, *args, **kwargs):
    """Initializes a native system dependency definition.

    Args:
      ??
    """
    super(NativePackage, self).__init__(*args, **kwargs)
    self.requires_root = True

  def check(self):
    return None

  def install(self):
    return False

  def _get_package_manager(self):
    # TODO(benvanik): switch _PackageManager type based on platform? detect?
    return None

  class _PackageManager(object):
    pass

  class _AptGetPackageManager(_PackageManager):
    pass

  class _MacPortsPackageManager(_PackageManager):
    pass

  class _HomebrewPackageManager(_PackageManager):
    pass


class DependencyManager(object):
  """
  """

  def __init__(self, cwd=None, *args, **kwargs):
    """
    Args:
      cwd: Current working directory.
    """
    self.cwd = cwd if cwd else os.getcwd()

  def scan_dependencies(self, target_rule_names):
    """Scans a list of target rules for their dependency information.

    Args:
      target_rule_names: A list of rule names that are to be executed.

    Returns:
      A de-duplicated list of Dependency definitions.
    """
    build_env = BuildEnvironment(root_path=self.cwd)
    module_resolver = FileModuleResolver(self.cwd)
    project = Project(module_resolver=module_resolver)
    dependencies = []
    with BuildContext(build_env, project,
                      task_executor=InProcessTaskExecutor(),
                      stop_on_error=False,
                      raise_on_error=False) as build_ctx:
      rule_sequence = build_ctx.rule_graph.calculate_rule_sequence(
          target_rule_names)
      for rule in rule_sequence:
        if hasattr(rule, 'requires'):
          dependencies.extend(rule.requires)
    # TODO(benvanik): de-duplicate
    return dependencies

  def install_all(self, dependencies):
    """Installs all of the given dependencies.

    Args:
      dependencies: A list of Dependency definitions to install.

    Returns:
      True if the installs succeeded.
    """
    # TODO(benvanik): sort by type first so batch install can be used
    raise NotImplementedError()

dependencies = []
