@ECHO OFF

SET DIR=%~dp0
python %DIR%\anvil\manage.py %*
