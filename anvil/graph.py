# Copyright 2012 Google Inc. All Rights Reserved.

"""Rule dependency graph.

A rule graph represents all of the rules in a project as they have been resolved
and tracked for dependencies. The graph can then be queried for various
information such as build rule sets/etc.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import networkx as nx

from anvil import project
from anvil import util


class RuleGraph(object):
  """A graph of rule nodes.
  """

  def __init__(self, project):
    """Initializes a rule graph.

    Args:
      project: Project to use for resolution.
    """
    self.project = project
    self.graph = nx.DiGraph()
    # A map of rule paths to rules, if they exist
    self.rule_nodes = {}

  def has_dependency(self, rule_path, predecessor_rule_path):
    """Checks to see if the given rule has a dependency on another rule.

    Args:
      rule_path: The name of the rule to check.
      predecessor_rule_path: A potential predecessor rule.

    Returns:
      True if by any way rule_path depends on predecessor_rule_path.

    Raises:
      KeyError: One of the given rules was not found.
    """
    if not rule_path in self.rule_nodes:
      raise KeyError('Rule "%s" not found' % (rule_path))
    if not predecessor_rule_path in self.rule_nodes:
      raise KeyError('Rule "%s" not found' % (predecessor_rule_path))
    return nx.has_path(self.graph, predecessor_rule_path, rule_path)

  def _ensure_rules_present(self, rule_paths, requesting_module=None):
    """Ensures that the given list of rules are present in the graph, and if not
    recursively loads them.

    Args:
      rule_paths: A list of target rule paths to add to the graph.
      requesting_module: Module that is requesting the given rules or None if
          all rule paths are absolute.
    """
    # Add all of the rules listed
    rules = []
    for rule_path in rule_paths:
      # Attempt to resolve the rule
      rule = self.project.resolve_rule(rule_path,
                                       requesting_module=requesting_module)
      if not rule:
        raise KeyError('Rule "%s" unable to be resolved' % (rule_path))
      rules.append(rule)
      print(rule)
      # If already present, ignore (no need to recurse)
      if rule.path in self.rule_nodes:
        continue

      # Add node to the graph
      self.rule_nodes[rule.path] = rule
      self.graph.add_node(rule.path)

      # Recursively resolve all dependent rules
      dependent_rule_paths = []
      for dep in rule.get_dependent_paths():
        if util.is_rule_path(dep):
          dependent_rule_paths.append(dep)
      if len(dependent_rule_paths):
        self._ensure_rules_present(dependent_rule_paths,
                                   requesting_module=rule.parent_module)

    # Add edges for all of the requested rules (at this point, all rules should
    # be added to the graph)
    for rule in rules:
      for dep in rule.get_dependent_paths():
        if util.is_rule_path(dep):
          dep_rule = self.project.resolve_rule(dep,
              requesting_module=rule.parent_module)
          # Node should exist due to recursive addition above
          assert dep_rule.path in self.rule_nodes
          self.graph.add_edge(dep_rule.path, rule.path)

    # Ensure the graph is a DAG (no cycles)
    if not nx.is_directed_acyclic_graph(self.graph):
      # TODO(benvanik): use nx.simple_cycles() to print the cycles
      raise ValueError('Cycle detected in the rule graph: %s' % (
          nx.simple_cycles(self.graph)))

  def add_rules_from_module(self, module):
    """Adds all rules (and their dependencies) from the given module.

    Args:
      module: A module with rules to add.
    """
    rule_paths = []
    for rule in module.rule_iter():
      rule_paths.append(rule.path)
    self._ensure_rules_present(rule_paths, requesting_module=module)

  def has_rule(self, rule_path):
    """Whether the graph has the given rule loaded.

    Args:
      rule_path: Full rule path.

    Returns:
      True if the given rule has been resolved and added to the graph.
    """
    return rule_path in self.rule_nodes

  def calculate_rule_sequence(self, target_rule_paths):
    """Calculates an ordered sequence of rules terminating with the given
    target rules.

    By passing multiple target names it's possible to build a combined sequence
    that ensures all the given targets are included with no duplicate
    dependencies.

    Args:
      target_rule_paths: A list of target rule paths to include in the
          sequence, or a single target rule path.

    Returns:
      An ordered list of Rule instances including all of the given target rules
      and their dependencies.

    Raises:
      KeyError: One of the given rules was not found.
    """
    if isinstance(target_rule_paths, str):
      target_rule_paths = [target_rule_paths]

    # Ensure the graph has everything required - if things go south this will
    # raise errors
    self._ensure_rules_present(target_rule_paths)

    # Reversed graph to make sorting possible
    # If this gets expensive (or many sequences are calculated) it could be
    # cached
    reverse_graph = self.graph.reverse()

    # Paths are added in reverse (from target to dependencies)
    sequence_graph = nx.DiGraph()

    def _add_rule_node_dependencies(rule_node):
      if sequence_graph.has_node(rule_node):
        # Already present in the sequence graph, no need to add again
        return
      # Add node
      sequence_graph.add_node(rule_node)
      # Recursively add all dependent children
      for out_edge in reverse_graph.out_edges_iter([rule_node]):
        out_rule_node = out_edge[1]
        if not sequence_graph.has_node(out_rule_node):
          _add_rule_node_dependencies(out_rule_node)
        sequence_graph.add_edge(rule_node, out_rule_node)

    # Add all paths for targets
    # Note that all nodes are present if we got this far, so no need to check
    for rule_path in target_rule_paths:
      rule = self.project.resolve_rule(rule_path)
      assert rule
      assert rule.path in self.rule_nodes
      _add_rule_node_dependencies(rule.path)

    # Reverse the graph so that it's dependencies -> targets
    reversed_sequence_graph = sequence_graph.reverse()

    # Get the list of nodes in sorted order
    rule_sequence = []
    for rule_node in nx.topological_sort(reversed_sequence_graph):
      rule_sequence.append(self.rule_nodes[rule_node])
    return rule_sequence
