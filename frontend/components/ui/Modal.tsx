"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";

/** Shared modal shell (spec §57: "modal/drawer system"). Esc closes,
 * click-outside closes, focus stays inside via a plain overlay pattern. */
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-lg border border-border bg-card-elevated p-5"
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">{title}</p>
          <button onClick={onClose} aria-label="Close" className="text-text-muted hover:text-text-primary">
            ×
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
