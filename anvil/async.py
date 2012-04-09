# Copyright 2012 Google Inc. All Rights Reserved.

__author__ = 'benvanik@google.com (Ben Vanik)'


class Deferred(object):
  """A simple deferred object, designed for single-threaded tracking of futures.
  """

  def __init__(self):
    """Initializes a deferred."""
    self._callbacks = []
    self._errbacks = []
    self._is_done = False
    self._failed = False
    self._exception = None
    self._args = None
    self._kwargs = None

  def is_done(self):
    """Whether the deferred has completed (either succeeded or failed).

    Returns:
      True if the deferred has completed.
    """
    return self._is_done

  def add_callback_fn(self, fn):
    """Adds a function that will be called when the deferred completes
    successfully.

    The arguments passed to the function will be those arguments passed to
    callback. If multiple callbacks are registered they will all be called with
    the same arguments, so don't modify them.

    If the deferred has already completed when this function is called then the
    callback will be made immediately.

    Args:
      fn: Function to call back.
    """
    if self._is_done:
      if not self._failed:
        fn(*self._args, **self._kwargs)
      return
    self._callbacks.append(fn)

  def add_errback_fn(self, fn):
    """Adds a function that will be called when the deferred completes with
    an error.

    The arguments passed to the function will be those arguments passed to
    errback. If multiple callbacks are registered they will all be called with
    the same arguments, so don't modify them.

    If the deferred has already completed when this function is called then the
    callback will be made immediately.

    Args:
      fn: Function to call back.
    """
    if self._is_done:
      if self._failed:
        fn(*self._args, **self._kwargs)
      return
    self._errbacks.append(fn)

  def callback(self, *args, **kwargs):
    """Completes a deferred successfully and calls any registered callbacks."""
    assert not self._is_done
    self._is_done = True
    self._args = args
    self._kwargs = kwargs
    callbacks = self._callbacks
    self._callbacks = []
    self._errbacks = []
    for fn in callbacks:
      fn(*args, **kwargs)

  def errback(self, *args, **kwargs):
    """Completes a deferred with an error and calls any registered errbacks."""
    assert not self._is_done
    self._is_done = True
    self._failed = True
    if len(args) and isinstance(args[0], Exception):
      self._exception = args[0]
    self._args = args
    self._kwargs = kwargs
    errbacks = self._errbacks
    self._callbacks = []
    self._errbacks = []
    for fn in errbacks:
      fn(*args, **kwargs)


def gather_deferreds(deferreds, errback_if_any_fail=False):
  """Waits until all of the given deferreds callback.
  Once all have completed this deferred will issue a callback
  with a list corresponding to each waiter, with a (success, args, kwargs)
  tuple for each deferred.

  The deferred returned by this will only ever issue callbacks, never errbacks.

  Args:
    deferreds: A list of deferreds to wait on.
    errback_if_any_fail: True to use errback instead of callback if at least one
        of the input deferreds fails.

  Returns:
    A deferred that is called back with a list of tuples corresponding to each
    input deferred. The tuples are of (success, args, kwargs) with success
    being a boolean True if the deferred used callback and False if it used
    errback.
  """
  if isinstance(deferreds, Deferred):
    deferreds = [deferreds]
  gather_deferred = Deferred()
  deferred_len = len(deferreds)
  if not deferred_len:
    gather_deferred.callback([])
    return gather_deferred

  pending = [deferred_len]
  result_tuples = deferred_len * [None]
  def _complete():
    pending[0] -= 1
    if not pending[0]:
      if not errback_if_any_fail:
        gather_deferred.callback(result_tuples)
      else:
        any_failed = False
        for result in result_tuples:
          if not result[0]:
            any_failed = True
            break
        if any_failed:
          gather_deferred.errback(result_tuples)
        else:
          gather_deferred.callback(result_tuples)

  def _makecapture(n, deferred):
    def _callback(*args, **kwargs):
      result_tuples[n] = (True, args, kwargs)
      _complete()
    def _errback(*args, **kwargs):
      result_tuples[n] = (False, args, kwargs)
      _complete()
    deferred.add_callback_fn(_callback)
    deferred.add_errback_fn(_errback)

  for n in xrange(deferred_len):
    _makecapture(n, deferreds[n])

  return gather_deferred
