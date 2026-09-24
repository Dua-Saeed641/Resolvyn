"""Probe retrieval scores for calibration.  Run from backend/:  .venv\\Scripts\\python scripts\\memory_probe.py"""

import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + (Path(__file__).resolve().parent.parent / "data" / "probe.db").as_posix()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
probe = Path(os.environ["DATABASE_URL"].replace("sqlite:///", ""))
if probe.exists():
    probe.unlink()

from app.database import init_db  # noqa: E402
from app.memory.memory_engine import memory  # noqa: E402
from app.services.seed_service import seed_all  # noqa: E402

init_db()
print(seed_all())
print(memory.stats())

QUERIES = [
    ("Billing", "I was charged twice for the same order and want one payment refunded"),
    ("Billing", "my refund has not arrived yet where is my refund"),
    ("Account", "my account is locked and I cannot log in"),
    ("Order", "my parcel is delayed where is my order shipment"),
    ("Order", "I want to cancel my order"),
    ("Technical", "my bluetooth headphones will not pair"),
    ("Technical", "the app keeps crashing when I open it"),
    ("Technical", "headphones flashing purple light error code P-77 after firmware update"),
    ("Technical", "my smart fridge is making a weird grinding noise and leaking coolant"),
    ("Other", "what are your support hours"),
    ("Other", "do you sell gift cards for corporate clients in Germany"),
    ("Billing", "payment deducted but order not confirmed"),
]
for dept, q in QUERIES:
    r = memory.retrieve(q, dept)
    top = r.top_hits(2)
    print(f"\n[{dept}] {q}\n   common={r.best_common:.2f} bug={r.best_bug:.2f}")
    for h in top:
        print(f"   {h.score:.2f} {h.via:6} {h.kind:10} {h.title[:70]}  {h.matched[:5]}")
