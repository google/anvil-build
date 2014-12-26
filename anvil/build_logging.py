"""Defines the anvil logging module.
"""

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
  def exception(self)
    """Gets the exception value on this WorkUnit or any children.
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
      should_listen(WorkUnit):Boolean - Should return true if this listener
          should listen to this WorkUnit. Gives a listener a chance to keep
          from receiving updates for a given WorkUnit.
      update(WorkUnit, String, *) - A method called when updates occur on a
          WorkUnit. The method is called with the WorkUnit that changed, the
          name of the attribute that was updated and the updated value.
    """
    if not listener.is_duplicate(self):
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
    """
    if self._waiting:
      for child in self.children:
        if not child._waiting:
          self._waiting = False
          break
    return self._waiting
