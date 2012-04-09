from anvil.manage import manage_command


@manage_command('test_command')
def test_command(args, cwd):
  return 0


# Duplicate name
@manage_command('test_command')
def test_command1(args, cwd):
  return 0
