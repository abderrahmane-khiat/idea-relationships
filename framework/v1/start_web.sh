#!/usr/bin/env sh
# Start the web version on http://127.0.0.1:8000
cd "$(dirname "$0")" && PYTHONPATH=src python -m idearel serve "$@"
