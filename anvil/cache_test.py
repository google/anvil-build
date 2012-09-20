#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the cache module.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import unittest2

import anvil.cache
from anvil.test import FixtureTestCase


class CacheTest(FixtureTestCase):
  """Behavioral tests for caching."""
  fixture = 'cache'

  def test(self):
    rule_cache = anvil.cache.FileRuleCache(self.root_path)
    rule_cache.save()


if __name__ == '__main__':
  unittest2.main()
