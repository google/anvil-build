@ECHO OFF

REM Copyright 2012 Google Inc. All Rights Reserved.
REM
REM wtf Windows setup script
REM Sets up a local virtualenv for anvil.
REM This places all dependencies within the anvil-build/ path such that nothing
REM from site-packages is used. In order to make use of this consumers should
REM invoke anvil-local.bat instead of the global 'anvil'.

SET DIR=%~dp0

REM Visual Studio 2010
SET VS90COMNTOOLS=%VS100COMNTOOLS%
REM Visual Studio 2012
REM SET VS90COMNTOOLS=%VS110COMNTOOLS%

ECHO Installing virtualenv (1.8.2)...

pip install virtualenv==1.8.2

ECHO Setting up the virtual environment...

virtualenv %DIR%\local_virtualenv

ECHO Preparing virtualenv...

REM Instead of using active we need to do it manually - the Windows
REM activate script doesn't return control back to this script when run.
SET VIRTUAL_ENV=%DIR%\local_virtualenv
SET PATH=%VIRTUAL_ENV%\Scripts;%PATH%
REM %DIR%\local_virtualenv\Scripts\activate

ECHO Repeatedly installing twisted, as python still doesn't support VS2010...
FOR %%A IN (1 2 3 4 5) DO pip install twisted

ECHO Installing anvil-build...
cd %DIR%
python setup.py develop
