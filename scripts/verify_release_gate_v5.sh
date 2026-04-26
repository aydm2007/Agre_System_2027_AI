#!/usr/bin/env bash
set -euo pipefail
make verify-v5-static
bash scripts/ops/preflight_enterprise.sh
