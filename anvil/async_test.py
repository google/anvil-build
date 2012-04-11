#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the async module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import unittest2

from anvil.async import Deferred, gather_deferreds
from anvil.test import AsyncTestCase


class DeferredTest(unittest2.TestCase):
  """Behavioral tests of the Deferred type."""

  def testMultiCall(self):
    d = Deferred()
    d.callback()
    with self.assertRaises(AssertionError):
      d.callback()
    d = Deferred()
    d.errback()
    with self.assertRaises(AssertionError):
      d.errback()
    d = Deferred()
    d.callback()
    with self.assertRaises(AssertionError):
      d.errback()
    d = Deferred()
    d.errback()
    with self.assertRaises(AssertionError):
      d.callback()

  def testCallbackArgs(self):
    cb = {}
    def cb_thunk(*args, **kwargs):
      cb['done'] = True
      cb['args'] = args
      cb['kwargs'] = kwargs

    d = Deferred()
    self.assertFalse(d.is_done())
    d.callback()
    self.assertTrue(d.is_done())

    d = Deferred()
    self.assertFalse(d.is_done())
    d.errback()
    self.assertTrue(d.is_done())

    d = Deferred()
    d.add_callback_fn(cb_thunk)
    d.callback()
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 0)
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.add_callback_fn(cb_thunk)
    d.callback('a', 'b')
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 2)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(cb['args'][1], 'b')
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.add_callback_fn(cb_thunk)
    d.callback('a', b='b')
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 1)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(len(cb['kwargs']), 1)
    self.assertEqual(cb['kwargs']['b'], 'b')
    cb.clear()

  def testCallbackOrder(self):
    cb = {}
    def cb_thunk(*args, **kwargs):
      cb['done'] = True
      cb['args'] = args
      cb['kwargs'] = kwargs

    d = Deferred()
    d.add_callback_fn(cb_thunk)
    d.callback('a')
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 1)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.callback('a')
    d.add_callback_fn(cb_thunk)
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 1)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.add_errback_fn(cb_thunk)
    d.errback('a')
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 1)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.errback('a')
    d.add_errback_fn(cb_thunk)
    self.assertNotEqual(len(cb), 0)
    self.assertTrue(cb['done'])
    self.assertEqual(len(cb['args']), 1)
    self.assertEqual(cb['args'][0], 'a')
    self.assertEqual(len(cb['kwargs']), 0)
    cb.clear()

    d = Deferred()
    d.add_callback_fn(cb_thunk)
    d.errback('a')
    self.assertEqual(len(cb), 0)
    cb.clear()

    d = Deferred()
    d.errback('a')
    d.add_callback_fn(cb_thunk)
    self.assertEqual(len(cb), 0)
    cb.clear()

    d = Deferred()
    d.add_errback_fn(cb_thunk)
    d.callback('a')
    self.assertEqual(len(cb), 0)
    cb.clear()

    d = Deferred()
    d.callback('a')
    d.add_errback_fn(cb_thunk)
    self.assertEqual(len(cb), 0)
    cb.clear()

  def testMultiCallbacks(self):
    cbs = []
    def cb_multi_thunk(*args, **kwargs):
      cbs.append({
          'done': True,
          'args': args,
          'kwargs': kwargs
          })

    d = Deferred()
    d.add_callback_fn(cb_multi_thunk)
    d.callback('a')
    self.assertEqual(len(cbs), 1)
    self.assertNotEqual(len(cbs[0]), 0)
    self.assertEqual(cbs[0]['args'][0], 'a')
    cbs[:] = []

    d = Deferred()
    d.add_callback_fn(cb_multi_thunk)
    d.add_callback_fn(cb_multi_thunk)
    d.callback('a')
    self.assertEqual(len(cbs), 2)
    self.assertNotEqual(len(cbs[0]), 0)
    self.assertNotEqual(len(cbs[1]), 0)
    self.assertEqual(cbs[0]['args'][0], 'a')
    self.assertEqual(cbs[1]['args'][0], 'a')
    cbs[:] = []

    d = Deferred()
    d.add_callback_fn(cb_multi_thunk)
    d.callback('a')
    d.add_callback_fn(cb_multi_thunk)
    self.assertEqual(len(cbs), 2)
    self.assertNotEqual(len(cbs[0]), 0)
    self.assertNotEqual(len(cbs[1]), 0)
    self.assertEqual(cbs[0]['args'][0], 'a')
    self.assertEqual(cbs[1]['args'][0], 'a')
    cbs[:] = []

    d = Deferred()
    d.callback('a')
    d.add_callback_fn(cb_multi_thunk)
    d.add_callback_fn(cb_multi_thunk)
    self.assertEqual(len(cbs), 2)
    self.assertNotEqual(len(cbs[0]), 0)
    self.assertNotEqual(len(cbs[1]), 0)
    self.assertEqual(cbs[0]['args'][0], 'a')
    self.assertEqual(cbs[1]['args'][0], 'a')
    cbs[:] = []


class GatherTest(AsyncTestCase):
  """Behavioral tests for the async gather function."""

  def testGather(self):
    d = gather_deferreds([])
    self.assertCallbackEqual(d, [])

    da = Deferred()
    db = Deferred()
    dc = Deferred()
    df = Deferred()
    d = gather_deferreds([da, db, dc, df])
    df.errback()
    dc.callback('c')
    db.callback('b')
    da.callback('a')
    self.assertCallbackEqual(d, [
        (True, ('a',), {}),
        (True, ('b',), {}),
        (True, ('c',), {}),
        (False, (), {})])

    da = Deferred()
    db = Deferred()
    dc = Deferred()
    df = Deferred()
    df.errback('f')
    dc.callback('c')
    d = gather_deferreds([da, db, dc, df])
    db.callback('b')
    da.callback('a')
    self.assertCallbackEqual(d, [
        (True, ('a',), {}),
        (True, ('b',), {}),
        (True, ('c',), {}),
        (False, ('f',), {})])

  def testErrback(self):
    d = gather_deferreds([], errback_if_any_fail=True)
    self.assertCallbackEqual(d, [])

    da = Deferred()
    db = Deferred()
    dc = Deferred()
    d = gather_deferreds([da, db, dc], errback_if_any_fail=True)
    dc.callback('c')
    db.callback('b')
    da.callback('a')
    self.assertCallbackEqual(d, [
        (True, ('a',), {}),
        (True, ('b',), {}),
        (True, ('c',), {})])

    da = Deferred()
    db = Deferred()
    dc = Deferred()
    df = Deferred()
    d = gather_deferreds([da, db, dc, df], errback_if_any_fail=True)
    df.errback()
    dc.callback('c')
    db.callback('b')
    da.callback('a')
    self.assertErrbackEqual(d, [
        (True, ('a',), {}),
        (True, ('b',), {}),
        (True, ('c',), {}),
        (False, (), {})])

    da = Deferred()
    db = Deferred()
    dc = Deferred()
    df = Deferred()
    df.errback('f')
    dc.callback('c')
    d = gather_deferreds([da, db, dc, df], errback_if_any_fail=True)
    db.callback('b')
    da.callback('a')
    self.assertErrbackEqual(d, [
        (True, ('a',), {}),
        (True, ('b',), {}),
        (True, ('c',), {}),
        (False, ('f',), {})])


if __name__ == '__main__':
  unittest2.main()
