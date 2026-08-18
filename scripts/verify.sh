#!/usr/bin/env bash
set -euo pipefail
python -m pytest -q
python -m gitgoblin.certify --output build/CERTIFICATE.json
