"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { CallPanel } from "@/components/customer/CallPanel";
import type { CustomerProfile } from "@/features/types";
import type { AgentStatus, CallStatus, Line } from "@/lib/useCall";

const CUSTOMERS: CustomerProfile[] = [
  { customer_id: "CUS-20481", name: "Lovekesh Anand", email: "lovekesh.anand@example.com", phone_last4: "4821", plan: "Premium", account_age_years: 3, recent_sentiment: "Neutral", open_issues: 0, previous_tickets: 7 },
];
const LINES: Line[] = [
  { id: "1", who: "agent", text: "Hi Lovekesh! This is Riya from Nova Retail. How can I help you today?" },
  { id: "2", who: "you", text: "I think I was charged twice for my earbuds." },
  { id: "3", who: "agent", text: "Oh no, twice? I can see two charges of 2,499 rupees on your card, 38 seconds apart. Want me to refund the extra one?" },
];

/** Design preview of the live call screen in each state (used for visual checks; no microphone needed). */
function Preview() {
  const q = useSearchParams();
  const state = (q.get("state") ?? "speaking") as AgentStatus;
  const status = (q.get("status") ?? "live") as CallStatus;
  return (
    <div className="mx-auto max-w-xl p-6">
      <CallPanel
        customers={CUSTOMERS}
        status={status}
        agentStatus={state}
        lines={LINES}
        interim={q.get("interim") ?? ""}
        error={null}
        muted={q.get("muted") === "1"}
        sttSupported
        ttsFallback={false}
        sttMode="server"
        customerId="CUS-20481"
        onCustomer={() => undefined}
        onStart={() => undefined}
        onSend={() => undefined}
        onEnd={() => undefined}
        onMute={() => undefined}
        onReset={() => undefined}
        agentName="Riya"
      />
    </div>
  );
}

export default function PreviewPage() {
  return (
    <Suspense fallback={null}>
      <Preview />
    </Suspense>
  );
}
