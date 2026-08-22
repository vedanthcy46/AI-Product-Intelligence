"""
run_all.py -- Plain-assert test runner (no pytest required).

Discovers every `test_*.py` module in this directory, executes it as a
subprocess, and aggregates pass/fail status.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    tests = sorted(f for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py") and f != "run_all.py")
    if not tests:
        print("No test modules found.")
        sys.exit(1)

    print("=" * 60)
    print(f"  RUNNING {len(tests)} TEST MODULES")
    print("=" * 60)
    failed = []
    for name in tests:
        path = os.path.join(HERE, name)
        print(f"\n>>> {name}")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run([sys.executable, path], cwd=ROOT, env=env)
        if result.returncode != 0:
            failed.append(name)

    print("\n" + "=" * 60)
    if failed:
        print(f"  FAILED MODULES ({len(failed)}): {', '.join(failed)}")
        print("=" * 60)
        sys.exit(1)
    print(f"  ALL {len(tests)} TEST MODULES PASSED (OK)")
    print("=" * 60)


if __name__ == "__main__":
    main()