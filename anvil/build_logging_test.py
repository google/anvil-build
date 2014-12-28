"""Test for the anvil logging components.
"""

__author__ = 'joshharrison@google.com'


import re
import unittest2

from mock import call
from mock import patch
from mock import MagicMock

from anvil import build_logging
from anvil import enums
from anvil import util


class WorkUnitTest(unittest2.TestCase):

  def testRecordWorkUnits(self):
    work_unit = build_logging.WorkUnit('test')
    self.assertEquals(enums.Status.WAITING, work_unit.get_status())
    work_unit.total = 10
    self.assertEquals(10, work_unit.total)
    work_unit.complete = 10
    self.assertEquals(10, work_unit.complete)

  def testAddChildUnit(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    self.assertEquals(parent, child.parent)
    self.assertEquals(1, len(parent.children))
    self.assertEquals(child, parent.children[0])

  def testAssumeChildCounts(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.total = 100
    child.total = 50
    parent.add_child(child)
    self.assertEquals(150, parent.total)
    child.total = 250
    self.assertEquals(350, parent.total)
    # Test idempotence
    child.total = 250
    self.assertEquals(350, parent.total)
    parent.total = 200
    self.assertEquals(450, parent.total)

    sibling = build_logging.WorkUnit('sibling')
    grandchild = build_logging.WorkUnit('grandchild')
    grandchild.total = 10
    sibling.add_child(grandchild)
    self.assertEquals(10, sibling.total)
    parent.add_child(sibling)
    self.assertEquals(460, parent.total)
    grandchild.total = 100
    sibling.total = 200
    self.assertEquals(750, parent.total)

  def testInvalidCountsThrowsError(self):
    work_unit = build_logging.WorkUnit('test')
    work_unit.complete = 100
    with self.assertRaises(ValueError):
      work_unit.total = 50

  def testGetChildStatuses(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    self.assertEquals(None, child.start_time)
    self.assertEquals(None, parent.start_time)
    self.assertEquals(enums.Status.WAITING, child.get_status())
    self.assertEquals(enums.Status.WAITING, parent.get_status())
    child.total = 20
    self.assertEquals(enums.Status.RUNNING, child.get_status())
    self.assertEquals(enums.Status.RUNNING, parent.get_status())
    parent.total = 30
    child.total = 0
    child.complete = 0
    self.assertEquals(enums.Status.SKIPPED, child.get_status())
    self.assertEquals(enums.Status.RUNNING, parent.get_status())
    parent.complete = 30
    self.assertEquals(enums.Status.SUCCEEDED, parent.get_status())

    child.exception = ValueError()
    self.assertEquals(enums.Status.FAILED, child.get_status())
    self.assertEquals(enums.Status.FAILED, parent.get_status())
    self.assertEquals(child.exception, parent.exception)

  def testChangeListenersCalled(self):
    mock_listener = MagicMock(name='listener')
    # If is_duplicate returns True, the listener will not be added to the
    # WorkUnit, and will therefor not have its handler triggered on
    # updates.
    mock_listener.should_listen.return_value = False
    test = build_logging.WorkUnit('test')
    test.add_change_listener(mock_listener)

    # Listeners should be triggered when updates occur anywhere along a WorkUnit
    # tree.
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    mock_child_listener = MagicMock(name='child_listener')
    mock_child_listener.should_listen.return_value = True
    mock_parent_listener = MagicMock(name='parent_listener')
    mock_parent_listener.should_listen.return_value = True
    child.add_change_listener(mock_child_listener)
    parent.add_change_listener(mock_parent_listener)

    child.total = 100
    parent.total = 100
    parent.complete = 100
    expected_child_calls = [
      call.should_listen(child),
      call.update(child, 'total', 100)
    ]
    expected_parent_calls = [
      call.should_listen(parent),
      call.update(parent, 'total', 100),
      call.update(parent, 'total', 200),
      call.update(parent, 'complete', 100)
    ]
    self.assertTrue(expected_child_calls == mock_child_listener.mock_calls)
    self.assertTrue(expected_parent_calls == mock_parent_listener.mock_calls)


class LogSourceTest(unittest2.TestCase):

  def testVerbosity(self):
    child_source = build_logging.LogSource(enums.Verbosity.VERBOSE)
    self.assertEquals(enums.Verbosity.VERBOSE, child_source.verbosity)
    child_source = build_logging.LogSource()
    self.assertEquals(enums.Verbosity.NORMAL, child_source.verbosity)
    child_source = build_logging.LogSource()
    parent_source = build_logging.LogSource(enums.Verbosity.VERBOSE)
    parent_source.add_child(child_source)
    self.assertEquals(enums.Verbosity.VERBOSE, child_source.verbosity)
    self.assertEquals(enums.Verbosity.VERBOSE, parent_source.verbosity)

  def testLogBasedOnVerbosity(self):
    log_source = build_logging.LogSource()
    log_source.verbosity = enums.Verbosity.SILENT
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1]
      log_source.log_debug('debug')
      log_source.log_info('info')
      log_source.log_warning('warning')
      log_source.log_error('error')
    expected = [
      (enums.LogLevel.ERROR, 1, None, 'error')
    ]
    self.assertListEqual(expected, log_source.buffered_messages)

    log_source = build_logging.LogSource()
    log_source.verbosity = enums.Verbosity.NORMAL
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1, 2, 3]
      log_source.log_debug('debug')
      log_source.log_info('info')
      log_source.log_warning('warning')
      log_source.log_error('error')
    expected = [
      (enums.LogLevel.INFO, 1, None, 'info'),
      (enums.LogLevel.WARNING, 2, None, 'warning'),
      (enums.LogLevel.ERROR, 3, None, 'error')
    ]
    self.assertListEqual(expected, log_source.buffered_messages)

    log_source = build_logging.LogSource()
    log_source.verbosity = enums.Verbosity.VERBOSE
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1, 2, 3, 4]
      log_source.log_debug('debug')
      log_source.log_info('info', 'test')
      log_source.log_warning('warning', 'test')
      log_source.log_error('error')
    expected = [
      (enums.LogLevel.DEBUG, 1, None, 'debug'),
      (enums.LogLevel.INFO, 2, 'test', 'info'),
      (enums.LogLevel.WARNING, 3, 'test', 'warning'),
      (enums.LogLevel.ERROR, 4, None, 'error')
    ]
    self.assertListEqual(expected, log_source.buffered_messages)

    log_source = build_logging.LogSource()
    # Inherit should default to normal of no parent exists.
    log_source.verbosity = enums.Verbosity.INHERIT
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1, 2, 3]
      log_source.log_debug('debug')
      log_source.log_info('info')
      log_source.log_warning('warning')
      log_source.log_error('error')
    expected = [
      (enums.LogLevel.INFO, 1, None, 'info'),
      (enums.LogLevel.WARNING, 2, None, 'warning'),
      (enums.LogLevel.ERROR, 3, None, 'error')
    ]
    self.assertListEqual(expected, log_source.buffered_messages)

  def testNoDuplicateLogSinks(self):
    log_sink = MagicMock()
    log_source = build_logging.LogSource()
    log_source.add_log_sink(log_sink)
    log_source.add_log_sink(log_sink)
    self.assertEquals(1, len(log_source.log_sinks))

  def testMessagesSentToLogSink(self):
    log_source = build_logging.LogSource(enums.Verbosity.VERBOSE)
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1, 2, 3, 4]
      log_source.log_debug('debug', 'bar')
      log_source.log_info('info', 'bar')
      log_source.log_warning('warning', 'foo')
      log_source.log_error('error', 'foo')
    log_sink = MagicMock()
    log_source.add_log_sink(log_sink)
    expected = [
      call.log((enums.LogLevel.DEBUG, 1, 'bar', 'debug')),
      call.log((enums.LogLevel.INFO, 2, 'bar', 'info')),
      call.log((enums.LogLevel.WARNING, 3, 'foo', 'warning')),
      call.log((enums.LogLevel.ERROR, 4, 'foo', 'error'))
    ]
    self.assertEquals(expected, log_sink.mock_calls)

    log_sink.mock_calls = []
    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [5]
      log_source.log_debug('debug', 'bar')
    expected = [
      call.log((enums.LogLevel.DEBUG, 5, 'bar', 'debug'))
    ]
    self.assertEquals(expected, log_sink.mock_calls)

  def testChildMessagesDetected(self):
    child_source = build_logging.LogSource(enums.Verbosity.INHERIT)
    parent_source = build_logging.LogSource(enums.Verbosity.VERBOSE)
    log_sink = MagicMock()
    parent_source.add_log_sink(log_sink)
    parent_source.add_child(child_source)

    with patch('__main__.util.timer') as mock_timer:
      mock_timer.side_effect = [1]
      child_source.log_debug('debug', 'foo')
    expected = [
      call.log((enums.LogLevel.DEBUG, 1, 'foo', 'debug'))
    ]
    self.assertEquals(expected, log_sink.mock_calls)
    

class WorkUnitLogSourceTest(unittest2.TestCase):

  def setUp(self):
    self.log_source = ls = build_logging.WorkUnitLogSource(
      enums.Verbosity.VERBOSE)

  def testAddingListenerGrabsStatus(self):
    work_unit = build_logging.WorkUnit(name='test')
    work_unit.add_change_listener(self.log_source)

    msgs = self.log_source.buffered_messages
    self.assertEquals(2, len(self.log_source.buffered_messages))
    self.assertEquals(enums.LogLevel.DEBUG, msgs[0][0])
    self.assertEquals('test', msgs[0][2])
    self.assertEquals(enums.LogLevel.INFO, msgs[1][0])
    self.assertEquals('test', msgs[1][2])

  def testWorkUnitLogging(self):
    work_unit = build_logging.WorkUnit(name='test')
    work_unit.add_change_listener(self.log_source)

    self.log_source.buffered_messages = []
    msgs = self.log_source.buffered_messages

    work_unit.total = 200
    self.assertEquals(2, len(self.log_source.buffered_messages))
    self.assertEquals(enums.LogLevel.DEBUG, msgs[0][0])
    self.assertEquals('test', msgs[0][2])
    self.assertEquals(enums.LogLevel.INFO, msgs[1][0])
    self.assertRegexpMatches(msgs[1][3], re.compile('0 of 200'))
    self.assertRegexpMatches(msgs[1][3], re.compile('[RUNNING]'))
    self.assertEquals('test', msgs[1][2])
    work_unit.complete = 10
    self.assertEquals(4, len(self.log_source.buffered_messages))
    self.assertEquals(enums.LogLevel.DEBUG, msgs[2][0])
    self.assertEquals('test', msgs[2][2])
    self.assertEquals(enums.LogLevel.INFO, msgs[3][0])
    self.assertRegexpMatches(msgs[3][3], re.compile('10 of 200'))
    self.assertRegexpMatches(msgs[3][3], re.compile('[RUNNING]'))
    self.assertEquals('test', msgs[3][2])

    work_unit.complete = 200
    self.assertEquals(6, len(self.log_source.buffered_messages))
    self.assertEquals(enums.LogLevel.DEBUG, msgs[4][0])
    self.assertEquals('test', msgs[4][2])
    self.assertEquals(enums.LogLevel.INFO, msgs[5][0])
    self.assertRegexpMatches(msgs[5][3], re.compile('[SUCCEEDED]'))
    self.assertEquals('test', msgs[5][2])

    work_unit.complete = 0
    work_unit.total = 0
    self.assertEquals(10, len(self.log_source.buffered_messages))
    self.assertEquals(enums.LogLevel.DEBUG, msgs[8][0])
    self.assertEquals('test', msgs[8][2])
    self.assertEquals(enums.LogLevel.INFO, msgs[9][0])
    self.assertRegexpMatches(msgs[9][3], re.compile('[SKIPPED]'))
    self.assertEquals('test', msgs[9][2])
    

if __name__ == '__main__':
  unittest2.main()
