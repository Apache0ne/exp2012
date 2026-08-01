@echo off
python tools\materialize_source.py
if errorlevel 1 exit /b %errorlevel%
python tools\build.py
