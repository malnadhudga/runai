@echo off
set "PYTHONPATH=%~dp0"
python -m runai.cli.main %*
