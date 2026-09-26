"""Benchmarks that need no running server or model: Jev's accuracy and speed, and retrieval quality.

  python -m benchmarks.offline        # prints one JSON document
"""

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp(prefix='resolvyn-bench-'), 'bench.db').as_posix()}"
os.environ["ENGINE_ENABLED"] = "false"
for k in ("CLOUD_LLM_API_KEY", "EMAIL_PASSWORD", "EMAIL_SMTP_HOST", "EMAIL_IMAP_HOST", "CUSTOMER_EMAILS"):
    os.environ[k] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks import datasets as D  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def jev_bench() -> dict:
    from app.judgment import jev

    out: dict = {}
    # routing
    dept_ok = intent_ok = 0
    misses = []
    by_dept: dict = {}
    for text, intent, dept in D.ROUTING:
        j = jev.rules_judge(text)
        dept_ok += j.department == dept
        intent_ok += j.intent == intent
        d = by_dept.setdefault(dept, [0, 0])
        d[1] += 1
        d[0] += j.department == dept
        if j.department != dept:
            misses.append({"said": text, "expected": dept, "got": j.department})
    n = len(D.ROUTING)
    out["routing"] = {"n": n, "department_accuracy": dept_ok / n, "intent_accuracy": intent_ok / n,
                      "per_department": {k: f"{v[0]}/{v[1]}" for k, v in by_dept.items()}, "misses": misses}
    # human request
    tp = fp = fn = tn = 0
    for text, want in D.HUMAN_REQUEST:
        got = jev.rules_judge(text).wants_human
        tp += got and want
        fp += got and not want
        fn += (not got) and want
        tn += (not got) and not want
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    out["human_request"] = {"n": len(D.HUMAN_REQUEST), "precision": prec, "recall": rec, "f1": 2 * prec * rec / max(prec + rec, 1e-9),
                            "wrong": [t for t, w in D.HUMAN_REQUEST if jev.rules_judge(t).wants_human != w]}
    out["heldout"] = {}
    ok_d = ok_i = 0
    miss_h = []
    for text, intent, dept in D.HELDOUT_ROUTING:
        j = jev.rules_judge(text)
        ok_d += j.department == dept
        ok_i += j.intent == intent
        if j.department != dept:
            miss_h.append({"said": text, "expected": dept, "got": j.department})
    out["heldout"]["routing"] = {"n": len(D.HELDOUT_ROUTING), "department_accuracy": ok_d / len(D.HELDOUT_ROUTING), "intent_accuracy": ok_i / len(D.HELDOUT_ROUTING), "misses": miss_h}
    tp = fp = fn = 0
    for text, want in D.HELDOUT_HUMAN:
        got = jev.rules_judge(text).wants_human
        tp += got and want
        fp += got and not want
        fn += (not got) and want
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    out["heldout"]["human_request"] = {"n": len(D.HELDOUT_HUMAN), "precision": prec, "recall": rec, "f1": 2 * prec * rec / max(prec + rec, 1e-9),
                                       "wrong": [t for t, w in D.HELDOUT_HUMAN if jev.rules_judge(t).wants_human != w]}
    # side talk
    ok = 0
    wrong = []
    for text, for_agent in D.ADDRESSEE:
        who, _ = jev.addressee(text, expecting_answer=False)
        pred_agent = who != "other"
        ok += pred_agent == for_agent
        if pred_agent != for_agent:
            wrong.append(text)
    out["side_talk"] = {"n": len(D.ADDRESSEE), "accuracy": ok / len(D.ADDRESSEE), "wrong": wrong}
    # dialogue acts
    ok = 0
    wrong = []
    for text, y, no, done in D.DIALOGUE:
        got = jev.dialogue_act(text)
        ok += got == (y, no, done)
        if got != (y, no, done):
            wrong.append(text)
    out["dialogue_acts"] = {"n": len(D.DIALOGUE), "accuracy": ok / len(D.DIALOGUE), "wrong": wrong}
    # how often would Jev ask a model for help
    unsure = sum(jev.is_unsure(t, jev.rules_judge(t)) for t, _, _ in D.ROUTING)
    out["routing"]["would_ask_model"] = unsure / n
    # speed: everything Jev does per caller sentence
    texts = [t for t, _, _ in D.ROUTING] * 60
    samples = []
    for t in texts:
        a = time.perf_counter()
        j = jev.rules_judge(t)
        jev.addressee(t, expecting_answer=False)
        jev.write_query(t, j)
        samples.append((time.perf_counter() - a) * 1000)
    out["speed"] = {"sentences": len(samples), "p50_ms": statistics.median(samples), "p95_ms": pct(samples, 95), "p99_ms": pct(samples, 99), "max_ms": max(samples)}
    return out


def retrieval_bench() -> dict:
    from fastapi.testclient import TestClient

    from app.judgment import jev
    from app.main import app
    from app.memory.memory_engine import memory

    with TestClient(app):  # startup seeds the built-in documents and history
        hit1 = hit3 = 0
        misses, lat = [], []
        for question, source, word in D.RETRIEVAL:
            j = jev.rules_judge(question)
            j.query = jev.write_query(question, j)
            t = time.perf_counter()
            hits = memory.retrieve(j.query, j.department).top_hits(3)
            lat.append((time.perf_counter() - t) * 1000)

            doc = source.replace(".md", "").replace("_", " ")

            def good(h):
                return (doc in (h.source or "").lower() or doc in h.title.lower()) and word in (h.title + " " + h.text).lower()

            hit1 += bool(hits) and good(hits[0])
            hit3 += any(good(h) for h in hits)
            if not (hits and good(hits[0])):
                misses.append({"question": question, "expected": source, "got": [f"{h.source or h.kind}: {h.title[-40:]}" for h in hits[:2]]})
        n = len(D.RETRIEVAL)
        return {"n": n, "hit_at_1": hit1 / n, "hit_at_3": hit3 / n, "p50_ms": statistics.median(lat), "p95_ms": pct(lat, 95),
                "chunks_indexed": len(memory.common), "misses": misses}


if __name__ == "__main__":
    result = {"jev": jev_bench(), "retrieval": retrieval_bench()}
    sys.stdout.reconfigure(encoding="utf-8")
    print("@@JSON@@" + json.dumps(result, ensure_ascii=False))
