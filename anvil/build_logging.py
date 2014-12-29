"""Defines the anvil logging module.
"""

__author__ = 'joshharrison@google.com'

from anvil import enums
from anvil import util


class WorkUnit(object):
  """A class used to keep track of work progress.

  The WorkUnit class uses total and complete metrics to keep track of work
  completed. WorkUnits can be chained in parent-child relationships with any
  updates to child WorkUnits being aggregated in the parent WorkUnit. The
  total/complete numbers are used to determine the current status of a given
  WorkUnit. Once an exception is set on a WorkUnit, its status automatically
  becomes FAILED along with all units up the parent chain.

  WorkUnits can also have change listeners attached. When the total, complete
  or exception attributes are updated on a WorkUnit, all listeners on that
  unit and all units up the parent chain are notified via a call to #update
  on the listener.
  """

  def __init__(self, name):
    self._complete = None
    self._total = None
    self._waiting = True
    self._exception = None

    self.name = name
    self.parent = None
    self.children = []
    self.listeners = []

    self.start_time = None
    self.end_time = None
    
  @property
  def complete(self):
    """Returns a complete count including all child WorkUnits.

    Returns:
      A number representing the total complete work units encompassed by this
      WorkUnit and all its child WorkUnits.
    """
    complete = 0
    for child in self.children:
      complete += child.complete
    if self._complete:
      complete += self._complete
    return complete

  @complete.setter
  def complete(self, complete):
    """Sets the complete count on this WorkUnit and validates all values.

    Args:
      complete: A number value corresponding to complete units of work.
    """
    self._complete = complete
    self._validate_and_update('complete')

  @property
  def total(self):
    """Returns a complete count including all parent WorkUnits.

    Returns:
      A number representing the total work units encompassed by this WorkUnit
      and all its child WorkUnits.
    """
    total = 0
    for child in self.children:
      total += child.total
    if self._total:
      total += self._total
    return total

  @total.setter
  def total(self, total):
    """Sets the total count on this WorkUnit and validates all values.

    Args:
      complete: A number value corresponding to total units of work.
    """
    self._total = total
    self._validate_and_update('total')

  @property
  def exception(self):
    """Gets the exception value on this WorkUnit or any children.

    Returns:
      An exception object or None if one is not set.
    """
    for child in self.children:
      if child.exception:
        return child.exception
    return self._exception

  @exception.setter
  def exception(self, exception):
    """Sets an exception on this work unit and validates all values.

    Args:
      exception: A Python exception object.
    """
    self._exception = exception
    self._validate_and_update('exception')

  def get_status(self):
    """Returns the status of this WorkUnit.

    The WorkUnit is in a WAITING state until either its exception, total or
    complete values are updated or any of its children change to a RUNNING
    state. The WorkUnit immediately goes to a FAILED state if an exception is
    set. If the total and completed units are both set to 0, the WorkUnit goes
    to a SKIPPED state. If total units are set and are greater than the number
    of completed units, it is set to a RUNNING state. Note that the complete
    and total units used for this determination include those set on any child
    WorkUnits. If total and complete are equal and greater than 0, then the
    WorkUnit is set to SUCCEEDED.

    Returns:
      An enums.Status value corresponding to the state this WorkUnit is in.
    """
    if self._is_waiting():
      return enums.Status.WAITING
    elif self.exception is not None:
      return enums.Status.FAILED
    elif self.total == 0 and self.complete == 0:
      return enums.Status.SKIPPED

    diff = (self.total or 0) - (self.complete or 0)
    if diff > 0:
      return enums.Status.RUNNING
    elif diff == 0:
      return enums.Status.SUCCEEDED

  def add_child(self, child):
    """Adds a child WorkUnit.

    Args:
      child: A child WorkUnit. The values of this child will be aggregated into
          the values of this object.
    """
    self.children.append(child)
    child.parent = self

  def add_change_listener(self, listener):
    """"Adds a change listener to this object.

    Change listeners will receive notifications of updates to values on this
    WorkUnit or any of its children. Listeners must implement the following
    methods:
      will_listen(WorkUnit):Boolean - Should return true if this listener
          should listen to this WorkUnit. Gives a listener a chance to keep
          from receiving updates for a given WorkUnit. If the listener returns
          True, it should be assumed that WorkUnit passed in will be run and
          will send updates to the listener.
      update(WorkUnit, String, *) - A method called when updates occur on a
          WorkUnit. The method is called with the WorkUnit that changed, the
          name of the attribute that was updated and the updated value.
    """
    if listener.should_listen(self):
      self.listeners.append(listener)

  def _validate_and_update(self, attribute):
    """Validates the current values on this WorkUnit and propegates updates.

    This method validates the current WorkUnit and performs any updates that
    occur as side-effects, such as updating the start and end time. This
    method also calls change listeners and propagates change calls to parent
    WorkUnits.

    Args:
      attribute: A string value corresponding to the name of the attribute
          that was updated.
    Raises:
      ValueError: A ValueError is raised if any of the current values are
          in an invalid state. For instance, if the completed count is greater
          that the total count.
    """
    if (not self._total == None and
        not self._complete == None and
        self._complete > self._total):
      raise ValueError('Complete tasks cannot be more than the total tasks.')
    if not self.start_time:
      self.start_time = util.timer()
    if self.total == self.complete and not self.total == None:
      self.end_time = util.timer()
    self._waiting = False
    for listener in self.listeners:
      listener.update(self, attribute, getattr(self, attribute))
    if self.parent:
      self.parent._validate_and_update(attribute)

  def _is_waiting(self):
    """Returns true iff this WorkUnit and all its child units are WAITING.

    Returns:
      True iff this WorkUnit and all its child units are WAITING.
    """
    if self._waiting:
      for child in self.children:
        if not child._waiting:
          self._waiting = False
          break
    return self._waiting


class LogSource(object):
  """A LogSource can be used to log messages filtered on a verbosity level.

  The LogSource class allows the buffered logging of messages at different
  severity levels and filtered off of Verbosity levels. LogSources can be part
  of a parent-child relationship, in which case child LogSources can make use
  of the parent's Verbosity level and LogSinks.

  Messages logged to a LogSource are buffered in the source's buffered_messages
  collection iff the severity of the message passes the Verbosity filter on the
  LogSource.
  """

  def __init__(self, verbosity=enums.Verbosity.INHERIT):
    """Sets up the LogSource with a default Verbosity of INHERIT.

    Args:
      verbosty: A enums.Verbosity value. Defaults to INHERIT. Note that if a
          parent LogSource does not exist, then this LogSource will use a NORMAL
          verbosity level.
    """
    self._verbosity = verbosity
    self.buffered_messages = []
    self.log_sinks = []
    self.parent = None

  @property
  def verbosity(self):
    """Returns the effective verbosity level of this LogSource.

    If this LogSource has a verbosity level of INHERIT and a parent exists, then
    this accessor will return the verbosity level of the parent.

    Returns:
      The enums.Verbosity level of this LogSource.
    """
    if not self.parent == None and self._verbosity == enums.Verbosity.INHERIT:
      return self.parent.verbosity
    elif self.parent == None and self._verbosity == enums.Verbosity.INHERIT:
      return enums.Verbosity.NORMAL
    return self._verbosity

  @verbosity.setter
  def verbosity(self, verbosity):
    """Sets the enums.Verbosity level of this LogSource.

    Args:
      verbosity: A enums.Verbosity level.
    """
    self._verbosity = verbosity

  def add_child(self, child):
    """Adds a child log source.

    Any LogSinks set on the parent will also be set on the child so that all
    messages from children are received.

    Args:
      child: A LogSource that will be a child of this LogSource.
    """
    child.parent = self
    for log_sink in self.log_sinks:
      child.add_log_sink(log_sink)

  def add_log_sink(self, log_sink):
    """Adds a LogSink to this LogSource.

    Adds a listening LogSink to this LogSource. If there any buffered messages,
    they are delegated synchronously to the added LogSink.

    Args:
      log_sink: A LogSink object capable of listening for LogSource messages.
    """
    if log_sink in self.log_sinks:
      return

    self.log_sinks.append(log_sink)
    for message in self.buffered_messages:
      log_sink.log(message)

  def log_debug(self, message, name=None):
    """Logs a message at DEBUG log level.

    DEBUG log level is only recorded on LogSources with VERBOSE verbosity.

    Args:
      message: A string message to be logged.
      name: A string name representing the source of the message. Defaults to
          none. How this is used is up to the LogSource.
    """
    if self._should_log(enums.LogLevel.DEBUG):
      message = '[%s] %s' % (
        enums.log_level_to_string(enums.LogLevel.DEBUG), message)
      self._log_internal(
        (enums.LogLevel.DEBUG, util.timer(), name, message))

  def log_info(self, message, name=None):
    """Logs a message at INFO log level.

    INFO log level is recorded on LogSources with VERBOSE or NORMAL verbosity.

    Args:
      message: A string message to be logged.
      name: A string name representing the source of the message. Defaults to
          none. How this is used is up to the LogSource.
    """
    if self._should_log(enums.LogLevel.INFO):
      message = '[%s] %s' % (
        enums.log_level_to_string(enums.LogLevel.INFO), message)
      self._log_internal(
        (enums.LogLevel.INFO, util.timer(), name, message))

  def log_warning(self, message, name=None):
    """Logs a message at WARNING log level.

    WARNING log level is recorded on LogSources with VERBOSE or NORMAL
    verbosity.

    Args:
      message: A string message to be logged.
      name: A string name representing the source of the message. Defaults to
          none. How this is used is up to the LogSource.
    """
    if self._should_log(enums.LogLevel.WARNING):
      message = '[%s] %s' % (
        enums.log_level_to_string(enums.LogLevel.WARNING), message)
      self._log_internal(
        (enums.LogLevel.WARNING, util.timer(), name, message))

  def log_error(self, message, name=None):
    """Logs a message at ERROR log level.

    ERROR log level is recorded on LogSources with any verbosity level.

    Args:
      message: A string message to be logged.
      name: A string name representing the source of the message. Defaults to
          none. How this is used is up to the LogSource.
    """
    if self._should_log(enums.LogLevel.ERROR):
      message = '[%s] %s' % (
        enums.log_level_to_string(enums.LogLevel.ERROR), message)
      self._log_internal(
        (enums.LogLevel.ERROR, util.timer(), name, message))

  def _should_log(self, level):
    """Determines whether a log message should be recorded.

    Given an enums.LogLevel value and the current enums.Verbosity level of this
    LogSource, this method determines whether the message should be recorded.

    Returns:
      Returns true if the passed in LogLevel should be recorded given the
      Verbosity level of this LogSource.
    """ 
    # Errors should always be shown.
    if level == enums.LogLevel.ERROR:
      return True
    # Otherwise, switch off of the log level and the current verbosity.
    if self.verbosity == enums.Verbosity.SILENT:
      return False
    elif self.verbosity == enums.Verbosity.NORMAL:
      if level == enums.LogLevel.DEBUG:
        return False
      else:
        return True
    elif self.verbosity == enums.Verbosity.VERBOSE:
      return True

  def _log_internal(self, message):
    """A private helper method for logging messages.

    Args:
      message: A tuple containing the LogLevel, the time the message was
          received, the name sent with the message and the mesage itself.
    """
    if self.log_sinks:
      for log_sink in self.log_sinks:
        log_sink.log(message)
    else:
      self.buffered_messages.append(message)


class WorkUnitLogSource(LogSource):
  """A LogSource meant to function as a listener on WorkUnits.
  """

  def __init__(self, verbosity=enums.Verbosity.INHERIT):
    super(WorkUnitLogSource, self).__init__(verbosity)

  def should_listen(self, work_unit):
    """All work_units should be listened to.

    Args:
      work_unit: The WorkUnit this listener is being asked to listen to.
    Returns:
      Returns True if the WorkUnit should be observed by this LogSource.
    """
    self.log_debug(
      'Adding listener to WorkUnit named \'%s\' with a status of %s.' %
      (work_unit.name, enums.status_to_string(work_unit.get_status())),
      work_unit.name)
    self.log_info(
      '%s: Logging %s' % (
        enums.status_to_string(work_unit.get_status()), work_unit.name),
      work_unit.name)
    return True

  def update(self, work_unit, attribute, value):
    """Receives updates from monitored WorkUnits.

    Given updates for monitored WorkUnits, this method transforms a WorkUnit
    update into a log message. It logs all calls to this method at DEBUG
    level, passing all arguments. It then logs formatted messages at INFO
    level recording the status of the WorkUnit being updated.

    Args:
      work_unit: The WorkUnit that was updated.
      attribute: The attribute who's value was updated.
      value: The new attribute value.
    """
    self.log_debug(
      'Received an update - WorkUnit: %s, Attr: %s, Value: %s' % (
        work_unit.name, attribute, value), work_unit.name)
    if work_unit.get_status() == enums.Status.RUNNING:
      running = enums.status_to_string(work_unit.get_status())
      self.log_info(
        '%s: %s - %s of %s' % (
          running, work_unit.name, work_unit.complete, work_unit.total),
        work_unit.name)
    else:
      status_string = enums.status_to_string(work_unit.get_status())
      self.log_info(
        '%s: %s' % (status_string, work_unit.name), work_unit.name)
          
      
