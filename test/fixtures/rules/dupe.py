# File with duplicate rules


from anvil.rule import Rule, build_rule


@build_rule('rule_d')
class RuleD1(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleD1, self).__init__(name, *args, **kwargs)


@build_rule('rule_d')
class RuleD2(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleD2, self).__init__(name, *args, **kwargs)
