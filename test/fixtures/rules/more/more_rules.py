# More (nested) rule types for testing rules


from anvil.rule import Rule, build_rule


@build_rule('rule_c')
class RuleC(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleC, self).__init__(name, *args, **kwargs)
