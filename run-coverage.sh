#!/bin/bash

# Copyright 2012 Google Inc. All Rights Reserved.

# This script runs the build unit tests with a coverage run and spits out
# the result HTML to scratch/coverage/

# TODO(benvanik): merge with run-tests.py?

# This must currently run from the root of the repo
# TODO(benvanik): make this runnable from anywhere (find git directory?)
if [ ! -d ".git" ]; then
  echo "This script must be run from the root of the repository (the folder containing .git)"
  exit 1
fi

# Get into a known-good initial state by removing everything
# (removes the possibility for confusing old output when runs fail)
if [ -e ".coverage" ]; then
  rm .coverage
fi
if [ -d "scratch/coverage" ]; then
  rm -rf scratch/coverage
fi

# Run all unit tests with coverage
coverage run --branch ./run-tests.py

# Dump to console (so you see *something*)
coverage report -m

# Output HTML report
coverage html -d scratch/coverage/

# Cleanup the coverage temp data, as it's unused and regenerated
if [ -e ".coverage" ]; then
  rm .coverage
fi
