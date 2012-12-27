#!/bin/bash

# Copyright 2012 Google Inc. All Rights Reserved.

# Sets up a local virtualenv for anvil.
# This places all dependencies within the anvil-build/ path such that nothing
# from site-packages is used. In order to make use of this consumers should
# invoke anvil-local.sh instead of the global 'anvil'.


DIR="$( cd "$( dirname "$0" )" && pwd )"


# Ensure virtualenv is present.
if [ ! -e "$(which virtualenv)" ]; then
  echo "virtualenv not found - installing..."
  if [ -e "$(which pip)" ]; then
    # Always install 1.8.2 on Windows - 1.8.4 is broken.
    # See: https://github.com/pypa/virtualenv/issues/373
    if [ -e "/Cygwin.bat" ]; then
      pip install virtualenv==1.8.2
    else
      sudo pip install virtualenv
    fi
  elif [-e "$(which easyinstall)" ]; then
    sudo easy_install virtualenv
  else
    echo "No python package installer found - aborting"
    echo "(get pip or easy_install)"
    exit 1
  fi
fi

# Setup the virtual environment.
virtualenv $DIR/local_virtualenv

# Install there.
source $DIR/local_virtualenv/bin/activate
cd $DIR
echo "running setup.py develop, this may take a moment..."
python setup.py --quiet develop
