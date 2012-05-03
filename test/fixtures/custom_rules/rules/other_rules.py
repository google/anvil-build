from anvil.rule import Rule, build_rule


@build_rule('other_rule')
class OtherRule(Rule):
  def __init__(self, name, *args, **kwargs):
    super(OtherRule, self).__init__(name, *args, **kwargs)
