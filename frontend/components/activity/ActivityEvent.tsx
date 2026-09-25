/** project.md §14: live activity stream entry. */
export function ActivityEvent({ timestamp, description }: { timestamp: string; description: string }) {
  return (
    <div className="flex gap-3 border-b border-border px-4 py-2 text-sm">
      <span className="w-20 shrink-0 text-text-muted">{timestamp}</span>
      <span className="text-text-body">{description}</span>
    </div>
  );
}
