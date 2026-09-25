"""Load a folder of your business documents into the AI's memory in one go.

  .venv\\Scripts\\python scripts\\ingest_folder.py D:\\my-company-docs
  .venv\\Scripts\\python scripts\\ingest_folder.py D:\\docs --kind sop --department Billing

Reads .pdf .docx .md .txt .csv .json (recursively). Each file is chunked, every section is routed to the right
department agent, and it is indexed into the vector memory and the knowledge graph, exactly like an upload on the
Knowledge page. Sub-folders can steer the type and department automatically:

  my-docs/sop/...  my-docs/business_logic/...  my-docs/product_db/...   (kind)
  my-docs/billing/...  my-docs/technical/...  my-docs/account/...  my-docs/order/...   (department)

The API does not have to be running: this writes to the same SQLite database. Stop the API first if it is running,
or use the Knowledge page instead. Run with --api http://localhost:8000 to upload through the running server.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KINDS = {"sop", "business_logic", "product_db"}
DEPTS = {"technical": "Technical", "billing": "Billing", "account": "Account", "order": "Order", "other": "Other"}
EXTS = {".pdf", ".docx", ".md", ".txt", ".csv", ".json"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--kind", choices=sorted(KINDS))
    ap.add_argument("--department", choices=list(DEPTS.values()))
    ap.add_argument("--api", help="upload through a running server instead of writing to the database directly")
    args = ap.parse_args()

    root = Path(args.folder)
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXTS and p.is_file())
    if not files:
        sys.exit(f"no .pdf/.docx/.md/.txt/.csv/.json files found under {root}")

    if not args.api:
        from app.database import init_db
        from app.memory.ingest import ingest_file
        from app.memory.memory_engine import memory

        init_db()
        memory.reload()
    else:
        import httpx

    total = 0
    for f in files:
        parts = {x.lower() for x in f.relative_to(root).parts[:-1]}
        kind = args.kind or next((k for k in KINDS if k in parts), None)
        dept = args.department or next((DEPTS[d] for d in DEPTS if d in parts), None)
        try:
            if args.api:
                r = httpx.post(f"{args.api.rstrip('/')}/api/knowledge/ingest", data={"kind": kind or "", "department": dept or ""},
                               files={"files": (f.name, f.read_bytes())}, timeout=120)
                r.raise_for_status()
                res = r.json()["ingested"][0]
            else:
                res = ingest_file(f.name, f.read_bytes(), kind=kind, department=dept)
            total += res["chunks"]
            print(f"  ok  {f.relative_to(root)}  -> {res['kind']}, {res['chunks']} chunks {res['departments']}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {f.relative_to(root)}: {e}")
    print(f"done: {len(files)} file(s), {total} chunks")


main()
