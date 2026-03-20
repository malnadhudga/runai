#!/usr/bin/env bash
# Dev launcher (repo root on PYTHONPATH). Prefer: pip install -e . && runai
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="${PWD}"
exec python -m runai.cli.main "$@"
