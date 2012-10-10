#!/bin/bash

# Copyright 2012 Google Inc. All Rights Reserved.

# Sets up a local virtualenv for anvil.
# This places all dependencies within the anvil-build/ path such that nothing
# from site-packages is used. In order to make use of this consumers should
# invoke anvil-local.sh instead of the global 'anvil'.


# Ensure virtualenv is present.
if [ ! -e "$(which virtualenv)" ]; then
  echo "virtualenv not found - installing..."
  if [ -e "$(which pip)" ]; then
    sudo pip install virtualenv
  elif [-e "$(which easyinstall)" ]; then
    sudo easy_install virtualenv
  else
    echo "No python package installer found - aborting"
    echo "(get pip or easy_install)"
    exit 1
  fi
fi

# Setup the virtual environment.
/usr/local/lib/python2.6/dist-packages/virtualenv-1.8.2-py2.6.egg/virtualenv.py local_virtualenv

# Install there.
source local_virtualenv/bin/activate
python setup.py develop
