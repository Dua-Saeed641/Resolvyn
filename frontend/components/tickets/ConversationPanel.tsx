import type { Message } from "@/features/tickets/types";
import { cx } from "@/lib/utils";

const SENDER_LABEL: Record<Message["sender"], string> = {
  CUSTOMER: "Customer",
  Resolvyn: "Resolvyn",
  HUMAN: "Operator",
};

/** spec §12: an operational support thread, not a chat-app UI — no bubbles,
 * no avatars, no emojis. */
export function ConversationPanel({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return <p className="text-xs text-text-muted">No conversation recorded for this ticket yet.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {messages.map((m) => (
        <div key={m.message_id} className="text-sm">
          <div className="flex items-center gap-2">
            <span
              className={cx(
                "text-xs font-medium",
                m.sender === "CUSTOMER" ? "text-text-primary" : m.sender === "HUMAN" ? "text-info" : "text-text-body"
              )}
            >
              {SENDER_LABEL[m.sender]}
            </span>
            <span className="text-[11px] text-text-muted">{new Date(m.timestamp).toLocaleTimeString(undefined, { hour12: false })}</span>
          </div>
          <p className="mt-0.5 text-text-body">{m.content}</p>
        </div>
      ))}
    </div>
  );
}
