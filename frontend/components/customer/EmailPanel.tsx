"use client";

import { Mail, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { CustomerProfile } from "@/features/types";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Msg = { from: string; incoming: boolean; subject: string; body: string; time: string };

/** Write to support by email. Riya answers in the same thread, from the same desks and tools as on a call. */
export function EmailPanel({ customer }: { customer?: CustomerProfile }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [ticket, setTicket] = useState<string | null>(null);
  const [thread, setThread] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // a different customer means a different mailbox: start clean
  useEffect(() => {
    setTicket(null);
    setThread([]);
    setError(null);
  }, [customer?.customer_id]);

  const send = async () => {
    if (!body.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ ticket_id: string; reply: unknown }>("/email/inbound", {
        from: customer?.email ?? "guest@example.com",
        subject: ticket ? `Re: ${subject} [${ticket}]` : subject || "Support request",
        text: body,
        ticket_id: ticket ?? undefined,
      });
      setTicket(r.ticket_id);
      setBody("");
      setThread(await api.get<Msg[]>(`/email/thread/${r.ticket_id}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send the email");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card aria-label="Email support">
      <div className="flex items-center justify-between gap-3 border-b px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
            <Mail className="h-4 w-4" /> Email us
          </h2>
          <p className="text-xs text-muted-foreground">Riya replies in the same thread. Sending as {customer ? customer.email : "a guest"}.</p>
        </div>
        {ticket && <Badge variant="muted">{ticket}</Badge>}
      </div>
      <div className="space-y-3 p-5">
        {thread.length > 0 && (
          <div className="max-h-72 space-y-3 overflow-y-auto pr-1">
            {thread.map((m, i) => (
              <div key={i} className={cn("rounded-lg border p-3 text-[13px]", m.incoming ? "bg-muted/40" : "bg-card")}>
                <p className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{m.from}</span>
                  <span>{m.incoming ? "You" : "Reply"}</span>
                </p>
                <p className="whitespace-pre-wrap leading-relaxed">{m.body}</p>
              </div>
            ))}
          </div>
        )}
        {!ticket && <Input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Subject" />}
        <Textarea placeholder={ticket ? "Reply…" : "Tell us what you need, for example: I think I was charged twice for my earbuds."} value={body} onChange={(e) => setBody(e.target.value)} aria-label="Message" rows={4} />
        {error && (
          <p role="alert" className="text-xs text-danger">
            {error}
          </p>
        )}
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">{busy ? "Riya is writing back…" : ticket ? "This continues your ticket." : "A ticket is created from your email."}</p>
          <Button onClick={send} disabled={busy || !body.trim()}>
            <Send /> {ticket ? "Send reply" : "Send email"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
