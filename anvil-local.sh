#!/bin/bash

# Copyright 2012 Google Inc. All Rights Reserved.

# Runs the local virtualenv copy of anvil instead of the global one.
# Requires that things be setup with ./setup-local.sh (which this will attempt
# to invoke if it notices things not quite right).


DIR="$( cd "$( dirname "$0" )" && pwd )"


# Check to see if setup.
if [ ! -d "$DIR/local_virtualenv" ]; then
  echo "Missing local virtualenv - setting up..."
  $DIR/setup-local.sh
fi


source $DIR/local_virtualenv/bin/activate
python $DIR/anvil/manage.py "$@"
