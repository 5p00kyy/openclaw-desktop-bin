#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
exec python3 -m unittest discover --start-directory "$repo_dir/tests" --pattern 'test_*.py' --verbose
