# Dummy file - this rule should not be discovered


from anvil.rule import Rule, build_rule


@build_rule('rule_x')
class RuleX(Rule):
  def __init__(self, name, *args, **kwargs):
    super(RuleX, self).__init__(name, *args, **kwargs)
