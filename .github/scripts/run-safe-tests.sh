#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .codex-venv
. .codex-venv/bin/activate
python -m pip install --disable-pip-version-check -r requirements.txt

# Gmail requires real credentials, while the YOLO suite requires Python 3.11 and
# a separately provisioned model. Both integration suites are excluded here.
PYTHONPATH=".:app:tests" python - <<'PY'
from pathlib import Path
import unittest

suite = unittest.TestSuite()
for path in sorted(Path("tests").glob("test_*.py")):
    if path.stem == "test_models":
        continue
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName(path.stem))

def filtered(test_suite):
    result = unittest.TestSuite()
    for test in test_suite:
        if isinstance(test, unittest.TestSuite):
            result.addTest(filtered(test))
        elif not test.id().endswith("test_gmail_send_uses_gmail_api_and_encodes_message"):
            result.addTest(test)
    return result

outcome = unittest.TextTestRunner(verbosity=2).run(filtered(suite))
raise SystemExit(0 if outcome.wasSuccessful() else 1)
PY
