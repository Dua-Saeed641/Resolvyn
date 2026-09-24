"use client";

import { useState } from "react";

import { useRealtime } from "@/lib/realtime";
import { cx } from "@/lib/utils";

/** spec §48: operational notifications — approval required, learning
 * signal created, ticket state changes. Session-only (not persisted). */
const LABELS: Record<string, string> = {
  ticket_updated: "Ticket updated",
  human_action_created: "Human intervention recorded",
  learning_signal_created: "Learning signal created",
};

export function NotificationBell() {
  const { notifications, unreadCount, markAllRead } = useRealtime();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => {
          setOpen((v) => !v);
          if (!open) markAllRead();
        }}
        className="relative flex items-center gap-1 text-text-muted hover:text-text-primary"
      >
        Notifications
        {unreadCount > 0 && (
          <span className="ml-1 rounded-full bg-info px-1.5 py-0.5 text-[10px] font-medium text-white">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-7 z-10 w-72 rounded border border-border bg-card-elevated shadow-lg">
          {notifications.length === 0 ? (
            <p className="p-3 text-xs text-text-muted">No notifications yet.</p>
          ) : (
            notifications.map((n, i) => (
              <div
                key={i}
                className={cx("border-b border-border px-3 py-2 text-xs last:border-b-0")}
              >
                <p className="text-text-primary">{LABELS[n.type] ?? n.type}</p>
                <p className="text-text-muted">
                  {typeof n.payload.ticket_id === "string" ? n.payload.ticket_id : ""}
                  {typeof n.payload.status === "string" ? ` — ${n.payload.status}` : ""}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
