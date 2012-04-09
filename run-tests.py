#!/usr/bin/python

# Copyright 2012 Google Inc. All Rights Reserved.

"""Python build system test runner.
In order to speed things up (and avoid some platform incompatibilities) this
script should be used instead of unit2 or python -m unittest.
"""

__author__ = 'benvanik@google.com (Ben Vanik)'


import os
import sys

# Add self to the root search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Run the tests
import anvil.test
anvil.test.main()
