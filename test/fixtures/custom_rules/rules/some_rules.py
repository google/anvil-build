from anvil.rule import Rule, build_rule


@build_rule('some_rule')
class SomeRule(Rule):
  def __init__(self, name, *args, **kwargs):
    super(SomeRule, self).__init__(name, *args, **kwargs)
