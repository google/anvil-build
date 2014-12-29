"""Defines anvil enums.
"""

class LogLevel:
  """Enumeration containing the types of log messages to display.
  """
  DEBUG = 0
  INFO = 1
  WARNING = 2
  ERROR = 3

class Status:
  """Provides work status values.
  """
  WAITING = 0
  RUNNING = 1
  SUCCEEDED = 2
  FAILED = 3
  SKIPPED = 4

class Verbosity:
  """Enumeration containing verbosity levels for logging.                                                                            
  SILENT = No logging.                                                                                                               
  NORMAL = Log info, warn and error.                                                                                                 
  VERBOSE = Log debug, info, warn and error.                                                                                         
  INHERIT = Use verbosity level of parent LogSource.                                                                                 
  """
  SILENT = 0
  NORMAL = 1
  VERBOSE = 2
  INHERIT = 3

def status_to_string(value):
  to_string_values = {
    Status.WAITING: 'WAITING',
    Status.RUNNING: 'RUNNING',
    Status.SUCCEEDED: 'SUCCEEDED',
    Status.FAILED: 'FAILED',
    Status.SKIPPED: 'SKIPPED'
  }
  return to_string_values[value]

def log_level_to_string(value):
  to_string_values = {
    LogLevel.DEBUG: 'DEBUG',
    LogLevel.INFO: 'INFO',
    LogLevel.WARNING: 'WARNING',
    LogLevel.ERROR: 'ERROR'
  }
  return to_string_values[value]
