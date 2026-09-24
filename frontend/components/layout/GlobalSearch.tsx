"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { Ticket } from "@/features/tickets/types";

/** spec §49: fast, minimal global search over ticket id/customer/agent/issue/order. */
export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<Ticket[]>("/tickets").then(setTickets).catch(() => setTickets([]));
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const q = query.trim().toLowerCase();
  const results =
    q.length === 0
      ? []
      : tickets
          .filter((t) =>
            [t.ticket_id, t.subject, t.intent, t.assigned_agent, t.order_id, t.customer_id]
              .filter(Boolean)
              .some((field) => String(field).toLowerCase().includes(q))
          )
          .slice(0, 8);

  return (
    <div ref={containerRef} className="relative w-64">
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search tickets, agents, orders..."
        className="w-full rounded border border-border bg-bg-primary px-2.5 py-1 text-xs text-text-primary placeholder:text-text-muted"
      />
      {open && results.length > 0 && (
        <div className="absolute right-0 top-8 z-10 w-80 rounded border border-border bg-card-elevated shadow-lg">
          {results.map((t) => (
            <Link
              key={t.ticket_id}
              href={`/tickets/${t.ticket_id}`}
              onClick={() => setOpen(false)}
              className="block border-b border-border px-3 py-2 text-xs last:border-b-0 hover:bg-card"
            >
              <span className="font-medium text-text-primary">{t.ticket_id}</span>
              <span className="ml-2 text-text-muted">{t.subject}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
