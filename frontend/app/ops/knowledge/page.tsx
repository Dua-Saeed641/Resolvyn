"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Button, Card, inputCls, Label } from "@/components/ui/primitives";
import { Pill } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { KnowledgeDoc, RulebookByDepartment } from "@/features/types";
import { api } from "@/lib/api";
import { DEPARTMENTS } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { useLive } from "@/lib/live";
import { cx } from "@/lib/utils";

type Hit = { chunk_id: number; title: string; kind: string; store: string; department: string; score: number; via: string; text?: string };

const KIND_LABEL: Record<string, string> = { sop: "SOP", business_logic: "Business logic", product_db: "Product DB" };
const SOURCE_LABEL: Record<string, string> = {
  human_teach: "Taught by a human",
  first_time_bug_suggestion: "First-time-bug suggestion",
  human_correction: "Human correction",
  seed: "Seed",
};

/** Answers "I do not know where the data is": ingest SOPs / business logic / product data,
 *  see them divided per department agent, and test what the AI would find. */
export default function KnowledgePage() {
  const { subscribe } = useLive();
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [book, setBook] = useState<RulebookByDepartment | null>(null);
  const [stats, setStats] = useState<{ documents: number; chunks: number; rules: number; graph: { nodes: number; edges: number } } | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [kind, setKind] = useState("");
  const [dept, setDept] = useState("");
  const [paste, setPaste] = useState({ title: "", text: "" });
  const [dept2, setDept2] = useState("Billing");
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ best_common: number; best_bug: number; hits: Hit[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [d, b, s] = await Promise.all([
        api.get<KnowledgeDoc[]>("/knowledge"),
        api.get<RulebookByDepartment>("/knowledge/rulebook/by-department"),
        api.get<typeof stats>("/knowledge/stats"),
      ]);
      setDocs(d);
      setBook(b);
      setStats(s);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    return subscribe((e) => {
      if (e.type === "rulebook_updated") load();
    });
  }, [load, subscribe]);

  const upload = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setBusy(true);
    setMsg(null);
    try {
      const form = new FormData();
      list.forEach((f) => form.append("files", f));
      if (kind) form.append("kind", kind);
      if (dept) form.append("department", dept);
      const r = await api.upload<{ ingested: { title: string; chunks: number; departments: Record<string, number> }[]; errors: { file: string; error: string }[] }>("/knowledge/ingest", form);
      const ok = r.ingested.map((d) => `${d.title}: ${d.chunks} chunks (${Object.entries(d.departments).map(([k, v]) => `${k} ${v}`).join(", ")})`);
      setMsg({ ok: r.errors.length === 0, text: [...ok, ...r.errors.map((e) => `${e.file}: ${e.error}`)].join(" · ") });
      await load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Upload failed" });
    } finally {
      setBusy(false);
    }
  };

  const savePaste = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const d = await api.post<{ title: string; chunks: number }>("/knowledge/ingest-text", { title: paste.title || "Untitled", text: paste.text, kind: kind || null, department: dept2 === "Auto" ? null : dept2 });
      setMsg({ ok: true, text: `${d.title}: ${d.chunks} chunks added to memory.` });
      setPaste({ title: "", text: "" });
      await load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Could not save" });
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    if (!q.trim()) return;
    setHits(await api.get(`/knowledge/search/test?q=${encodeURIComponent(q)}`));
  };

  return (
    <AppShell title="Knowledge">
      <div className="mx-auto max-w-[1400px] space-y-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            ["Documents", stats?.documents],
            ["Memory chunks", stats?.chunks],
            ["Rulebook entries", stats?.rules],
            ["Graph nodes / edges", stats ? `${stats.graph.nodes} / ${stats.graph.edges}` : undefined],
          ].map(([l, v]) => (
            <div key={l as string} className="rounded-lg border border-border bg-card px-4 py-3">
              <p className="text-[11px] uppercase tracking-wide text-text-muted">{l}</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-text-primary">{v ?? "—"}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card title="Ingest data" subtitle="SOPs, business logic, product data — PDF, DOCX, Markdown, TXT, CSV, JSON">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                upload(e.dataTransfer.files);
              }}
              className={cx("rounded-lg border border-dashed px-4 py-8 text-center", drag ? "border-text-primary bg-card-elevated" : "border-border")}
            >
              <p className="text-sm text-text-primary">Drop files here</p>
              <p className="mt-0.5 text-xs text-text-muted">Each document is chunked, routed to the right department agent, and indexed into the vector memory and the knowledge graph.</p>
              <input ref={fileRef} type="file" multiple hidden accept=".pdf,.docx,.md,.txt,.csv,.json" onChange={(e) => e.target.files && upload(e.target.files)} />
              <Button className="mt-3" disabled={busy} onClick={() => fileRef.current?.click()}>
                {busy ? "Ingesting…" : "Choose files"}
              </Button>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div>
                <Label>Type</Label>
                <select className={inputCls} value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="">Auto-detect</option>
                  <option value="sop">SOP</option>
                  <option value="business_logic">Business logic</option>
                  <option value="product_db">Product DB</option>
                </select>
              </div>
              <div>
                <Label>Department</Label>
                <select className={inputCls} value={dept} onChange={(e) => setDept(e.target.value)}>
                  <option value="">Auto-classify per section</option>
                  {DEPARTMENTS.map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-5 border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium text-text-primary">Or paste text</p>
              <input className={cx(inputCls, "mb-2")} placeholder="Title, e.g. Warranty claims SOP" value={paste.title} onChange={(e) => setPaste({ ...paste, title: e.target.value })} />
              <textarea className={cx(inputCls, "min-h-[96px]")} placeholder="Paste the procedure, policy or product details…" value={paste.text} onChange={(e) => setPaste({ ...paste, text: e.target.value })} />
              <div className="mt-2 flex items-center gap-2">
                <select aria-label="Department for pasted text" className={cx(inputCls, "w-auto")} value={dept2} onChange={(e) => setDept2(e.target.value)}>
                  <option>Auto</option>
                  {DEPARTMENTS.map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
                <Button variant="primary" disabled={busy || !paste.text.trim()} onClick={savePaste}>
                  Save to memory
                </Button>
              </div>
            </div>
            {msg && (
              <p role="status" className={cx("mt-3 text-xs", msg.ok ? "text-success" : "text-danger")}>
                {msg.ok ? "✓ " : "✕ "}
                {msg.text}
              </p>
            )}
          </Card>

          <Card title="Retrieval tester" subtitle="What would the AI find for this caller sentence?">
            <div className="flex gap-2">
              <input className={inputCls} placeholder="e.g. my headphones show error P-77 after the update" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && test()} />
              <Button variant="primary" onClick={test}>
                Test
              </Button>
            </div>
            {hits && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-text-muted">
                  Best match: common memory <span className="text-text-primary">{hits.best_common.toFixed(2)}</span> · first-time-bug memory <span className="text-text-primary">{hits.best_bug.toFixed(2)}</span>
                  {hits.best_common < 0.28 && hits.best_bug < 0.28 && <span className="ml-2 text-danger">→ would be flagged as a first-time bug</span>}
                </p>
                {hits.hits.map((h) => (
                  <div key={h.chunk_id} className="rounded border border-border bg-bg-secondary p-2.5">
                    <div className="flex items-center justify-between gap-2 text-[13px]">
                      <span className="truncate text-text-primary">{h.title}</span>
                      <span className="tabular-nums text-text-body">{h.score.toFixed(2)}</span>
                    </div>
                    <p className="text-[11px] text-text-muted">
                      {h.kind.replace("_", " ")} · {h.department} · {h.via}
                    </p>
                    {h.text && <p className="mt-1 line-clamp-3 text-xs text-text-body">{h.text}</p>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <Card title="Rulebook by department" subtitle="Each department agent only consults its own slice (plus general policy)" bodyClass="p-0">
          {!book ? (
            <p className="p-4 text-sm text-text-muted">Loading…</p>
          ) : (
            <div className="grid divide-y divide-border md:grid-cols-5 md:divide-x md:divide-y-0">
              {DEPARTMENTS.map((d) => (
                <div key={d} className="p-4">
                  <p className="text-sm font-medium text-text-primary">{d} Agent</p>
                  <p className="mt-0.5 text-[11px] text-text-muted">
                    {book[d].sop_chunks} SOP sections · {book[d].rules.length} rule{book[d].rules.length === 1 ? "" : "s"}
                  </p>
                  <ul className="mt-2 space-y-0.5 text-[11px] text-text-secondary">
                    {book[d].documents.slice(0, 4).map((s) => (
                      <li key={s} className="truncate">
                        {s}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 space-y-2">
                    {book[d].rules.map((r) => (
                      <div key={r.rule_id} className="group rounded border border-border bg-bg-secondary p-2">
                        <p className="text-xs font-medium text-text-primary">{r.topic}</p>
                        <p className="mt-0.5 line-clamp-4 text-[11px] text-text-body">{r.knowledge}</p>
                        <div className="mt-1 flex items-center justify-between">
                          <Pill tone={r.source === "first_time_bug_suggestion" ? "danger" : "info"}>{SOURCE_LABEL[r.source] ?? r.source}</Pill>
                          <button className="text-[11px] text-text-secondary hover:text-danger" onClick={() => api.del(`/knowledge/rulebook/${r.rule_id}`).then(load)} aria-label={`Delete rule ${r.topic}`}>
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Documents" subtitle="Everything the AI can ground its answers in" bodyClass="p-0">
          {loading ? (
            <p className="p-4 text-sm text-text-muted">Loading…</p>
          ) : docs.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No documents yet" description="Upload your SOPs above. Until then the AI has nothing to ground answers in and will flag every problem as a first-time bug." />
            </div>
          ) : (
            <table className="w-full text-left text-[13px]">
              <thead className="border-b border-border text-[11px] uppercase tracking-wide text-text-secondary">
                <tr>
                  <th className="px-4 py-2 font-medium">Document</th>
                  <th className="px-2 py-2 font-medium">Type</th>
                  <th className="px-2 py-2 font-medium">Category</th>
                  <th className="px-2 py-2 font-medium">Used by</th>
                  <th className="px-2 py-2 text-right font-medium">Chunks</th>
                  <th className="px-2 py-2 font-medium">Updated</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.document_id} className="border-b border-border/60 last:border-b-0">
                    <td className="px-4 py-2 text-text-primary">{d.title}</td>
                    <td className="px-2 py-2 text-text-muted">{KIND_LABEL[d.kind] ?? d.kind}</td>
                    <td className="px-2 py-2 text-text-muted">{d.category}</td>
                    <td className="px-2 py-2 text-text-body">{d.department} Agent</td>
                    <td className="px-2 py-2 text-right tabular-nums">{d.chunk_count}</td>
                    <td className="px-2 py-2 text-text-muted">{fmtDateTime(d.last_updated)}</td>
                    <td className="px-4 py-2 text-right">
                      <button className="text-xs text-text-secondary hover:text-danger" onClick={() => api.del(`/knowledge/${d.document_id}`).then(load)} aria-label={`Delete ${d.title}`}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
