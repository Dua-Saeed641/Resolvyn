"""Run every email benchmark and print one line per benchmark.

  .venv\\Scripts\\python scripts\\email_benchmark.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
env = {**os.environ, "ENGINE_ENABLED": "false"}
out = subprocess.run([sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests/test_email_benchmarks.py"], cwd=ROOT, env=env,
                     capture_output=True, text=True).stdout

GROUP = {"B01": "Protocol", "B05": "Content", "B11": "Plain text", "B12": "Presentation", "B18": "Inbound and safety", "B22": "Transport", "B24": "Threads"}
rows = re.findall(r"test_(B\d+)_(\w+) (PASSED|FAILED)", out)
print("Resolvyn email benchmarks\n")
group = ""
for bid, name, result in rows:
    group = GROUP.get(bid, group)
    if bid in GROUP:
        print(f"\n{group}")
    print(f"  {'PASS' if result == 'PASSED' else 'FAIL'}  {bid}  {name.replace('_', ' ')}")
passed = sum(1 for r in rows if r[2] == "PASSED")
print(f"\n{passed}/{len(rows)} benchmarks passed")
sys.exit(0 if rows and passed == len(rows) else 1)
