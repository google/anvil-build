from anvil.manage import ManageCommand


class TestCommand(ManageCommand):
  def __init__(self):
    super(TestCommand, self).__init__(name='test_command')


class TestCommand1(ManageCommand):
  def __init__(self):
    super(TestCommand1, self).__init__(name='test_command')
