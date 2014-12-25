"""Defines the anvil logging module.
"""

from anvil import enums
from anvil import util


class WorkUnit(object):
  """A class used to keep track of work progress.
  """

  def __init__(self, name):
    self._completed = None
    self._total = None
    self._waiting = True
    self._exception = None

    self.name = name
    self.children = []
    self.parent = None

    self.start_time = None
    self.end_time = None
    
  @property
  def completed(self):
    completed = 0
    for child in self.children:
      completed += child.completed
    if self._completed:
      completed += self._completed
    return completed

  @completed.setter
  def completed(self, completed):
    self._completed = completed
    self._validate_and_update_times()

  @property
  def total(self):
    total = 0
    for child in self.children:
      total += child.total
    if self._total:
      total += self._total
    return total

  @total.setter
  def total(self, total):
    self._total = total
    self._validate_and_update_times()

  @property
  def exception(self):
    for child in self.children:
      if child.exception:
        return child.exception
    return self._exception

  @exception.setter
  def exception(self, exception):
    self._exception = exception
    self._validate_and_update_times()

  def _validate_and_update_times(self):
    if (not self._total == None and
        not self._completed == None and
        self._completed > self._total):
      raise ValueError('Completed tasks cannot be more than the total tasks.')
    if not self.start_time:
      self.start_time = util.timer()
    if self.total == self.completed and not self.total == None:
      self.end_time = util.timer()
    self._waiting = False

  def _is_waiting(self):
    if self._waiting:
      for child in self.children:
        if not child._waiting:
          self._waiting = False
          break
    return self._waiting

  def get_status(self):
    if self._is_waiting():
      return enums.Status.WAITING
    elif self.exception is not None:
      return enums.Status.FAILED
    elif self.total == 0 and self.completed == 0:
      return enums.Status.SKIPPED

    diff = (self.total or 0) - (self.completed or 0)
    if diff > 0:
      return enums.Status.RUNNING
    elif diff == 0:
      return enums.Status.SUCCEEDED

  def add_child(self, child):
    self.children.append(child)
    child.parent = self
