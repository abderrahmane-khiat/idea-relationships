@echo off
rem Start the web version on http://127.0.0.1:8000
cd /d "%~dp0"
set PYTHONPATH=src
python -m idearel serve %*
