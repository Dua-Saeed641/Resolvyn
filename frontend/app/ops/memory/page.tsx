"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/EmptyState";
import type { GraphSnapshot } from "@/features/types";
import { api } from "@/lib/api";
import { useLive } from "@/lib/live";

const TYPE_STYLE: Record<string, { fill: string; label: string; r: number }> = {
  department: { fill: "hsl(var(--foreground))", label: "Department agent", r: 11 },
  document: { fill: "hsl(var(--info))", label: "Document (SOP / business logic / product)", r: 8 },
  ticket: { fill: "hsl(var(--success))", label: "Solved ticket (episodic memory)", r: 6 },
  rule: { fill: "hsl(var(--warning))", label: "Rulebook entry", r: 7 },
  bug: { fill: "hsl(var(--danger))", label: "First-time bug", r: 7 },
  customer: { fill: "hsl(var(--text-secondary))", label: "Customer", r: 5 },
  concept: { fill: "hsl(var(--divider))", label: "Concept", r: 4 },
};

interface P {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/** The knowledge-graph half of the memory (docs/architecture.md §2.6), built from every ingested
 *  SOP and every solved ticket. A small force layout is computed client-side; no library. */
export default function MemoryPage() {
  const { tickets, subscribe } = useLive();
  const [g, setG] = useState<GraphSnapshot | null>(null);
  const [pos, setPos] = useState<Record<string, { x: number; y: number }>>({});
  const [hover, setHover] = useState<string | null>(null);
  const [limit, setLimit] = useState(120);
  const solved = Object.values(tickets).filter((t) => t.status === "RESOLVED").length;
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = () => api.get<GraphSnapshot>(`/knowledge/graph/snapshot?limit=${limit}`).then(setG);
  useEffect(() => {
    load();
    return subscribe((e) => {
      if (e.type === "ticket_update" && e.ticket.status === "RESOLVED") {
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(load, 2500);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit, subscribe]);

  useEffect(() => {
    if (!g) return;
    const W = 1000;
    const H = 640;
    const pts: P[] = g.nodes.map((n, i) => {
      const a = (i / g.nodes.length) * Math.PI * 2;
      return { id: n.id, x: W / 2 + Math.cos(a) * 260 + Math.random() * 30, y: H / 2 + Math.sin(a) * 200 + Math.random() * 30, vx: 0, vy: 0 };
    });
    const idx = new Map(pts.map((p, i) => [p.id, i]));
    for (let it = 0; it < 260; it++) {
      const cool = 1 - it / 260;
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x;
          const dy = pts[i].y - pts[j].y;
          const d2 = dx * dx + dy * dy + 0.01;
          const f = (1800 / d2) * cool;
          const d = Math.sqrt(d2);
          pts[i].vx += (dx / d) * f;
          pts[i].vy += (dy / d) * f;
          pts[j].vx -= (dx / d) * f;
          pts[j].vy -= (dy / d) * f;
        }
      }
      for (const e of g.edges) {
        const a = pts[idx.get(e.src) ?? -1];
        const b = pts[idx.get(e.dst) ?? -1];
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const f = (d - 70) * 0.012 * cool;
        a.vx += (dx / d) * f;
        a.vy += (dy / d) * f;
        b.vx -= (dx / d) * f;
        b.vy -= (dy / d) * f;
      }
      for (const p of pts) {
        p.vx += (W / 2 - p.x) * 0.002;
        p.vy += (H / 2 - p.y) * 0.002;
        p.x += Math.max(-12, Math.min(12, p.vx));
        p.y += Math.max(-12, Math.min(12, p.vy));
        p.vx *= 0.6;
        p.vy *= 0.6;
        p.x = Math.max(20, Math.min(W - 20, p.x));
        p.y = Math.max(20, Math.min(H - 20, p.y));
      }
    }
    setPos(Object.fromEntries(pts.map((p) => [p.id, { x: p.x, y: p.y }])));
  }, [g]);

  const neighbours = useMemo(() => {
    if (!g || !hover) return new Set<string>();
    const s = new Set<string>([hover]);
    for (const e of g.edges) {
      if (e.src === hover) s.add(e.dst);
      if (e.dst === hover) s.add(e.src);
    }
    return s;
  }, [g, hover]);

  const hovered = g?.nodes.find((n) => n.id === hover);

  return (
    <AppShell title="Memory">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-3xl text-sm text-text-muted">
            The AI builds this graph itself: every ingested SOP adds concepts and department links, and every solved query ({solved} so far) becomes an episodic
            memory linked to the concepts, documents and customer involved. A new call is answered from both the vector index and this graph.
          </p>
          <label className="flex items-center gap-2 text-xs text-text-muted">
            Nodes shown
            <select className="rounded border border-border bg-bg-secondary px-2 py-1 text-text-primary" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[60, 120, 200, 300].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>

        <Card
          bodyClass="p-0"
          title="Knowledge graph"
          subtitle={g ? `${g.stats.nodes} nodes · ${g.stats.edges} edges in memory (showing the ${g.nodes.length} strongest)` : "Loading…"}
          right={<span className="text-xs text-text-muted">{hovered ? `${hovered.type}: ${hovered.label}` : "Hover a node"}</span>}
        >
          {!g || g.nodes.length === 0 ? (
            <div className="p-4">
              <EmptyState title="The graph is empty" description="Ingest SOPs on the Knowledge page, or resolve a few tickets, and the graph will grow." />
            </div>
          ) : (
            <svg viewBox="0 0 1000 640" className="h-[640px] w-full" role="img" aria-label="Knowledge graph of concepts, documents, departments and solved tickets">
              <g>
                {g.edges.map((e, i) => {
                  const a = pos[e.src];
                  const b = pos[e.dst];
                  if (!a || !b) return null;
                  const lit = hover && neighbours.has(e.src) && neighbours.has(e.dst);
                  return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={lit ? "hsl(var(--foreground))" : "hsl(var(--border))"} strokeWidth={lit ? 1.2 : 0.7} opacity={hover && !lit ? 0.25 : 1} />;
                })}
              </g>
              <g>
                {g.nodes.map((n) => {
                  const p = pos[n.id];
                  if (!p) return null;
                  const st = TYPE_STYLE[n.type] ?? TYPE_STYLE.concept;
                  const dim = hover && !neighbours.has(n.id);
                  const showLabel = n.type !== "concept" || neighbours.has(n.id) || n.weight >= 6;
                  return (
                    <g key={n.id} transform={`translate(${p.x},${p.y})`} opacity={dim ? 0.25 : 1} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
                      <circle r={st.r + Math.min(4, Math.log2(n.weight + 1))} fill={st.fill} />
                      {showLabel && (
                        <text y={-(st.r + 6)} textAnchor="middle" fontSize={n.type === "concept" ? 9 : 10} fill="hsl(var(--text-body))">
                          {n.label.length > 26 ? n.label.slice(0, 25) + "…" : n.label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
          <ul className="flex flex-wrap gap-x-5 gap-y-1 border-t border-border px-4 py-3 text-[11px] text-text-muted">
            {Object.entries(TYPE_STYLE).map(([k, s]) => (
              <li key={k} className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.fill }} aria-hidden />
                {s.label}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}
