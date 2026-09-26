"""Vector half of the memory (docs/architecture.md §2.6).

A sparse TF-IDF vector index with idf-weighted term coverage. Sparse vectors
are the honest choice for a 4 GB-VRAM machine: every GB goes to the language
model, retrieval stays on the CPU and is explainable. The class is deliberately
small so a dense embedder can replace `_vector()` later without touching callers.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.memory.text import tokens


@dataclass
class Hit:
    chunk_id: int
    title: str
    text: str
    department: str
    kind: str
    store: str
    score: float
    source: str | None = None
    ref_ticket_id: str | None = None
    via: str = "vector"  # vector | graph
    matched: list[str] = field(default_factory=list)
    rank: float = 0.0  # ordering only: score plus the heading bonus (never used as a confidence)

    def public(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "kind": self.kind,
            "store": self.store,
            "department": self.department,
            "score": round(self.score, 2),
            "via": self.via,
            "ref_ticket_id": self.ref_ticket_id,
        }


class VectorIndex:
    def __init__(self, store: str) -> None:
        self.store = store
        self._chunks: list[dict] = []
        self._vecs: list[dict[str, float]] = []
        self._norms: list[float] = []
        self._terms: list[set[str]] = []
        self._headings: list[set[str]] = []  # the words of each section's own heading
        self._idf: dict[str, float] = {}

    def __len__(self) -> int:
        return len(self._chunks)

    def rebuild(self, chunks: list[dict]) -> None:
        self._chunks = chunks
        docs = []
        for c in chunks:
            # The title counts double: SOP headings are the strongest topic signal.
            docs.append(tokens(c["title"] + " " + c["title"] + " " + c["text"], expand=True))
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        n = max(len(docs), 1)
        self._idf = {t: math.log(1 + (n + 1) / (f + 0.5)) for t, f in df.items()}
        self._vecs, self._norms, self._terms = [], [], []
        self._headings = [set(tokens(re.split(r"\s+[—-]\s+", c["title"])[-1])) for c in chunks]
        for d in docs:
            tf = Counter(d)
            vec = {t: (1 + math.log(c)) * self._idf[t] for t, c in tf.items()}
            self._vecs.append(vec)
            self._norms.append(math.sqrt(sum(v * v for v in vec.values())) or 1.0)
            self._terms.append(set(tf))

    def search(
        self,
        query: str,
        k: int = 4,
        *,
        department: str | None = None,
        kinds: set[str] | None = None,
    ) -> list[Hit]:
        q_tokens = tokens(query, expand=True)
        if not q_tokens or not self._chunks:
            return []
        qtf = Counter(q_tokens)
        q_plain = set(tokens(query))
        default_idf = max(self._idf.values(), default=1.0)
        qvec = {t: (1 + math.log(c)) * self._idf.get(t, default_idf * 0.5) for t, c in qtf.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        total_weight = sum(qvec.values()) or 1.0

        scored: list[Hit] = []
        for i, c in enumerate(self._chunks):
            if kinds and c["kind"] not in kinds:
                continue
            vec = self._vecs[i]
            dot = sum(w * vec.get(t, 0.0) for t, w in qvec.items())
            if dot <= 0:
                continue
            cosine = dot / (qnorm * self._norms[i])
            matched = [t for t in qvec if t in self._terms[i]]
            coverage = sum(qvec[t] for t in matched) / total_weight
            # Blend: coverage answers "does this chunk explain what was asked",
            # cosine keeps long, unfocused chunks from winning by accident.
            score = 0.6 * coverage + 0.4 * min(1.0, cosine * 1.6)
            rank_bonus = 0.45 if (c["kind"] not in ("past_query", "rule", "bug") and self._headings[i] and self._headings[i] <= q_plain) else 0.0  # asked about exactly this section
            if department and c["department"] == department:
                score *= 1.12
            elif department and c["department"] not in (department, "Other"):
                score *= 0.85
            scored.append((rank_bonus,
                Hit(
                    chunk_id=c["chunk_id"], title=c["title"], text=c["text"], department=c["department"],
                    kind=c["kind"], store=self.store, score=min(score, 1.0), rank=min(score, 1.0) + rank_bonus, source=c.get("source"),
                    ref_ticket_id=c.get("ref_ticket_id"), matched=matched,
                )
            ))
        # The heading bonus only re-orders results ("warranty" puts the Warranty section first); it never raises a score,
        # so it cannot turn an unfamiliar problem into a "known path".
        scored.sort(key=lambda bh: bh[1].score + bh[0], reverse=True)
        return [h for _, h in scored[:k]]
