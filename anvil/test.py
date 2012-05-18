# Copyright 2012 Google Inc. All Rights Reserved.

"""Base test case for tests that require static file fixtures.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import io
import os
import tempfile
import shutil
import sys
import unittest2

from anvil import util


def main():
  """Entry point for running tests.
  """
  # Collect tests
  tests = collector()

  # Run the tests in the default runner
  test_runner = unittest2.runner.TextTestRunner(verbosity=2)
  test_runner.run(tests)


def collector():
  """Collects test for the setuptools test_suite command.
  """
  # Only find test_*.py files under anvil/
  loader = unittest2.TestLoader()
  return loader.discover('anvil',
                         pattern='*_test.py',
                         top_level_dir='.')


class AsyncTestCase(unittest2.TestCase):
  """Test case adding additional asserts for async results."""

  def assertCallback(self, deferred):
    self.assertTrue(deferred.is_done())
    done = []
    def _callback(*args, **kwargs):
      done.append(True)
    def _errback(*args, **kwargs):
      self.fail('Deferred failed when it should have succeeded')
    deferred.add_errback_fn(_errback)
    deferred.add_callback_fn(_callback)
    if not len(done):
      self.fail('Deferred not called back with success')

  def assertCallbackEqual(self, deferred, value):
    self.assertTrue(deferred.is_done())
    done = []
    def _callback(*args, **kwargs):
      self.assertEqual(args[0], value)
      done.append(True)
    def _errback(*args, **kwargs):
      self.fail('Deferred failed when it should have succeeded')
    deferred.add_errback_fn(_errback)
    deferred.add_callback_fn(_callback)
    if not len(done):
      self.fail('Deferred not called back with success')

  def assertErrback(self, deferred):
    self.assertTrue(deferred.is_done())
    done = []
    def _callback(*args, **kwargs):
      self.fail('Deferred succeeded when it should have failed')
    def _errback(*args, **kwargs):
      done.append(True)
    deferred.add_callback_fn(_callback)
    deferred.add_errback_fn(_errback)
    if not len(done):
      self.fail('Deferred not called back with error')

  def assertErrbackEqual(self, deferred, value):
    self.assertTrue(deferred.is_done())
    done = []
    def _callback(*args, **kwargs):
      self.fail('Deferred succeeded when it should have failed')
    def _errback(*args, **kwargs):
      self.assertEqual(args[0], value)
      done.append(True)
    deferred.add_callback_fn(_callback)
    deferred.add_errback_fn(_errback)
    if not len(done):
      self.fail('Deferred not called back with error')

  def assertErrbackWithError(self, deferred, error_cls):
    self.assertTrue(deferred.is_done())
    done = []
    def _callback(*args, **kwargs):
      self.fail('Deferred succeeded when it should have failed')
    def _errback(exception=None, *args, **kwargs):
      done.append(True)
      self.assertIsInstance(exception, error_cls)
    deferred.add_callback_fn(_callback)
    deferred.add_errback_fn(_errback)
    if not len(done):
      self.fail('Deferred not called back with error')


class FixtureTestCase(AsyncTestCase):
  """Test case supporting static fixture/output support.
  Set self.fixture to a folder name from the test/fixtures/ path.
  """

  def setUp(self):
    super(FixtureTestCase, self).setUp()

    # Root output path
    self.temp_path = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.temp_path)
    self.root_path = self.temp_path

    # Copy fixture files
    if self.fixture:
      self.root_path = os.path.join(self.root_path, self.fixture)
      build_path = util.get_anvil_path()
      if not build_path:
        raise Error('Unable to find build path')
      fixture_path = os.path.join(
          build_path, '..', 'test', 'fixtures', self.fixture)
      target_path = os.path.join(self.temp_path, self.fixture)
      shutil.copytree(fixture_path, target_path)

  def assertFileContents(self, path, contents):
    self.assertTrue(os.path.isfile(path))
    with io.open(path, 'rt') as f:
      file_contents = f.read()
    self.assertEqual(file_contents, contents)
