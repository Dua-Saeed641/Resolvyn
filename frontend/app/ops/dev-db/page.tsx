"use client";

/** TEMPORARY — a raw, read-only database browser for local development
 *  without the model running. Not linked from the sidebar on purpose (it is
 *  not a real product page). Open it directly at /ops/dev-db.
 *
 *  To remove this feature later: delete this file, delete
 *  backend/app/api/routes/dev_db.py, and remove its one `include_router`
 *  line (marked "TEMPORARY") in backend/app/api/router.py. Nothing else
 *  depends on any of it.
 */

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";

interface TableInfo {
  name: string;
  row_count: number;
}

interface TableData {
  table: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

function cellText(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function DevDbPage() {
  const [tables, setTables] = useState<TableInfo[] | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [data, setData] = useState<TableData | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const limit = 50;

  useEffect(() => {
    api
      .get<{ tables: TableInfo[] }>("/dev-db/tables")
      .then((r) => {
        setTables(r.tables);
        if (r.tables.length > 0) setSelected((cur) => cur || r.tables[0].name);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load table list"));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setError(null);
    api
      .get<TableData>(`/dev-db/tables/${selected}?limit=${limit}&offset=${offset}`)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load table"));
  }, [selected, offset]);

  return (
    <AppShell title="Dev: Database Viewer (temporary)">
      <div className="mx-auto max-w-[1400px] space-y-4">
        <div className="rounded-lg border border-dashed border-warning/40 bg-warning/5 p-3 text-xs text-warning">
          Temporary dev tool — raw, read-only DB rows, for building frontend screens without the model running.
          Safe to delete later (see this page&apos;s own file header for exactly what to remove).
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="flex flex-wrap items-center gap-2">
          {tables === null ? (
            <p className="text-sm text-muted-foreground">Loading tables…</p>
          ) : (
            <select
              className="rounded border bg-background px-3 py-1.5 text-sm"
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setOffset(0);
              }}
            >
              {tables.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.row_count})
                </option>
              ))}
            </select>
          )}
        </div>

        {data && (
          <div className="rounded-lg border bg-card">
            <div className="flex items-center justify-between border-b px-4 py-2.5 text-xs text-muted-foreground">
              <span>
                {data.table}: showing {data.rows.length ? data.offset + 1 : 0}–{data.offset + data.rows.length} of {data.total}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
                  Previous
                </Button>
                <Button variant="outline" size="sm" disabled={offset + limit >= data.total} onClick={() => setOffset(offset + limit)}>
                  Next
                </Button>
              </div>
            </div>
            {data.rows.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">No rows in this table.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    {data.columns.map((c) => (
                      <TableHead key={c} className="whitespace-nowrap">
                        {c}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.rows.map((row, i) => (
                    <TableRow key={i}>
                      {data.columns.map((c) => (
                        <TableCell key={c} className="max-w-[280px] truncate whitespace-nowrap" title={cellText(row[c])}>
                          {cellText(row[c])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
