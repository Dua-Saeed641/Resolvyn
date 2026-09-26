"""Run the Resolvyn benchmarks and write benchmarks/results.json and docs/benchmarks.md.

  .venv\\Scripts\\python -m benchmarks.run                       # everything (about 25 minutes, uses the GPU)
  .venv\\Scripts\\python -m benchmarks.run --sections offline    # only what needs no model (seconds)
  .venv\\Scripts\\python -m benchmarks.run --sections truth --reps 2
"""

import argparse
import asyncio
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchmarks import live  # noqa: E402

ALL = ["offline", "engine", "resolution", "truth", "learning", "jev_model", "email"]


def offline() -> dict:
    out = subprocess.run([sys.executable, "-m", "benchmarks.offline"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return json.loads(out.split("@@JSON@@", 1)[1])


def hardware() -> dict:
    cpu = ram = ""
    try:
        cpu = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"], capture_output=True, text=True).stdout.strip()
        ram = subprocess.run(["powershell", "-NoProfile", "-Command", "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"], capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return {"cpu": cpu, "ram_gb": ram, "os": platform.platform(), "gpu": live.gpu()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default="all")
    ap.add_argument("--reps", type=int, default=5, help="repetitions of each adversarial truth scenario, per mode")
    ap.add_argument("--out", default=str(ROOT / "benchmarks" / "results.json"))
    a = ap.parse_args()
    sections = ALL if a.sections == "all" else a.sections.split(",")
    result: dict = {"when": time.strftime("%Y-%m-%d %H:%M"), "hardware": hardware(), "model": "Qwen3.5-4B Q4_K_M (fast tier), local", "reps": a.reps}

    if "offline" in sections:
        print("offline: Jev accuracy and speed, retrieval ...", flush=True)
        result["offline"] = offline()
    if "engine" in sections:
        print("engine: decode speed of the local model ...", flush=True)
        result["engine"] = live.engine_speed()
    live_sections = [s for s in sections if s in ("resolution", "truth", "learning", "jev_model", "email")]
    if live_sections:
        print("starting the server with the local model ...", flush=True)
        srv = live.Server(engine=True)
        try:
            srv.start()
            result["server"] = {"ready_seconds": round(srv.load_s, 1)}
            part = asyncio.run(live.run(live_sections, a.reps, progress=lambda m: print(m, flush=True)))
            result.update({k: v for k, v in part.items() if k != "gpu"})
            result["gpu_loaded"] = live.gpu()
        finally:
            srv.stop()
    if "email" in sections:
        print("email: the 25 protocol and content benchmarks ...", flush=True)
        result["email_tests"] = live.email_tests()

    Path(a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
