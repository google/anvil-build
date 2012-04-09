# Dummy rule types for testing rules


from anvil.rule import Rule, build_rule


@build_rule('rule_a')
class RuleA(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleA, self).__init__(name, *args, **kwargs)


@build_rule('rule_b')
class RuleB(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleB, self).__init__(name, *args, **kwargs)
