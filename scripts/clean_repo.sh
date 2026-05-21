#!/usr/bin/env bash
set -euo pipefail

find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '*.egg-info' -o -name 'build' -o -name 'dist' \) -prune -print -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -print -delete
