"use client";

import { useState } from "react";

/** project.md §25: human correction input. */
export function CorrectionDialog({ onSubmit }: { onSubmit: (correction: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="rounded border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Correct action</p>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="mt-2 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
        rows={3}
        placeholder="Correct action:"
      />
      <button
        onClick={() => onSubmit(value)}
        className="mt-2 rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary"
      >
        Submit correction
      </button>
    </div>
  );
}
