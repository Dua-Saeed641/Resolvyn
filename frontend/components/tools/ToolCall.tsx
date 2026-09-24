/** project.md §18: tool/API activity line — ✓ Completed / → Waiting / ○ Not started. */
const STATE_MARK: Record<string, string> = {
  COMPLETED: "✓",
  WAITING: "→",
  NOT_STARTED: "○",
  FAILED: "✗",
};

export function ToolCall({ name, status }: { name: string; status: keyof typeof STATE_MARK }) {
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 text-sm">
      <span
        className={status === "FAILED" ? "text-danger" : status === "COMPLETED" ? "text-success" : "text-text-muted"}
      >
        {STATE_MARK[status]}
      </span>
      <span className="font-mono text-text-body">{name}</span>
    </div>
  );
}
