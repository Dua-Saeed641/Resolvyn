"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { cx } from "@/lib/utils";

type Row = Record<string, string | number | boolean | null>;
type Snapshot = { orders: Row[]; payments: Row[]; shipments: Row[]; accounts: Row[]; customers: Row[] };
type Lookup = { found: boolean; match: string; order?: Row; candidates?: Row[] };

const TABS: { key: keyof Snapshot; label: string; cols: string[] }[] = [
  { key: "orders", label: "Orders", cols: ["order_id", "customer_id", "item", "amount", "placed", "status", "shipment_id"] },
  { key: "payments", label: "Payments", cols: ["transaction_id", "order_id", "amount", "status", "method", "timestamp"] },
  { key: "shipments", label: "Shipments", cols: ["shipment_id", "carrier", "status", "location", "eta", "delayed", "delay_reason"] },
  { key: "customers", label: "Customers", cols: ["customer_id", "name", "email", "phone_last4", "plan"] },
  { key: "accounts", label: "Accounts", cols: ["customer_id", "status", "failed_logins", "locked_reason"] },
];

/** The business records the department agents look up: orders, payments, shipments, customers, account state. */
export default function BusinessDataPage() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [tab, setTab] = useState<keyof Snapshot>("orders");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [ref, setRef] = useState("");
  const [found, setFound] = useState<Lookup | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api.get<Snapshot>("/business/data").then(setData).catch(() => setData(null));
  }, []);
  useEffect(load, [load]);

  const importFile = async (file: File) => {
    setMsg(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api.upload<{ kind: string; imported: number }>("/business/import", form);
      setMsg({ ok: true, text: `Imported ${r.imported} ${r.kind}. The agents use them immediately.` });
      load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Import failed" });
    }
  };
  const lookup = async () => {
    if (!ref.trim()) return;
    setFound(await api.get<Lookup>(`/business/orders/lookup?ref=${encodeURIComponent(ref.trim())}`));
  };

  const current = TABS.find((t) => t.key === tab)!;
  const rows = data?.[tab] ?? [];

  return (
    <AppShell title="Business data">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Import your own records" subtitle="CSV or JSON: orders (order_id,item,…), payments (transaction_id,order_id,…), shipments (shipment_id,carrier,…) or customers (customer_id,name,…). Existing IDs are updated.">
            <input ref={fileRef} type="file" hidden accept=".csv,.json" onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} />
            <button onClick={() => fileRef.current?.click()} className="rounded bg-text-max px-3.5 py-2 text-sm font-medium text-black">Choose a file</button>
            {msg && <p role="status" className={cx("mt-2 text-xs", msg.ok ? "text-success" : "text-danger")}>{msg.text}</p>}
          </Card>
          <Card title="Order lookup tester" subtitle="What the order desk finds for whatever a caller says: ORD-83921, 83921, or just the last digits.">
            <div className="flex gap-2">
              <input className="w-full rounded border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary" placeholder="83921" aria-label="Order reference" value={ref} onChange={(e) => setRef(e.target.value)} onKeyDown={(e) => e.key === "Enter" && lookup()} />
              <button onClick={lookup} className="rounded border border-border px-3.5 py-2 text-sm text-text-primary hover:bg-card-elevated">Find</button>
            </div>
            {found && (
              <p className="mt-2 text-xs text-text-body">
                {found.found && found.order
                  ? `${found.match === "exact" ? "Found" : "Matched by the last digits"}: ${found.order.order_id}, ${found.order.item}, ${found.order.status}`
                  : found.match === "ambiguous"
                    ? `Several orders match: ${(found.candidates ?? []).map((o) => o.order_id).join(", ")}`
                    : "No order matches. The agent will say so plainly and ask for the ID or the registered email."}
              </p>
            )}
          </Card>
        </div>

        <Card bodyClass="p-0">
          <div className="flex gap-1 border-b border-border px-3 pt-2">
            {TABS.map((t) => (
              <button key={t.key} onClick={() => setTab(t.key)} className={cx("rounded-t px-3 py-2 text-sm", tab === t.key ? "bg-card-elevated text-text-primary" : "text-text-muted hover:text-text-primary")}>
                {t.label} <span className="text-xs text-text-muted">{data?.[t.key].length ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-text-muted">
                  {current.cols.map((c) => <th key={c} className="px-4 py-2 font-medium">{c.replace(/_/g, " ")}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={current.cols.length} className="px-4 py-6 text-text-muted">No {current.label.toLowerCase()} yet. Import a file above.</td></tr>
                )}
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-border last:border-b-0">
                    {current.cols.map((c) => <td key={c} className="px-4 py-2 text-text-body">{r[c] === null || r[c] === undefined || r[c] === "" ? "·" : String(r[c])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
