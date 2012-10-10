#!/bin/bash

# Copyright 2012 Google Inc. All Rights Reserved.

# Runs the local virtualenv copy of anvil instead of the global one.
# Requires that things be setup with ./setup-local.sh (which this will attempt
# to invoke if it notices things not quite right).


# Check to see if setup.
if [ ! -d "local_virtualenv" ]; then
  echo "Missing local virtualenv - setting up..."
  ./setup-local.sh
fi


source local_virtualenv/bin/activate
python anvil/manage.py "$@"
