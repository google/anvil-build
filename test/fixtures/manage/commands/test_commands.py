from anvil.manage import ManageCommand


class TestCommand(ManageCommand):
  def __init__(self):
    super(TestCommand, self).__init__(name='test_command')

  def execute(self, args, cwd):
    return 123
