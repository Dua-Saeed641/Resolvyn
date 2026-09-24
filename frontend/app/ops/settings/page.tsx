"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card, Kv } from "@/components/ui/primitives";
import { Pill } from "@/components/ui/StatusBadge";
import type { SystemInfo } from "@/features/types";
import { api } from "@/lib/api";

/** What is actually running: local models through the epsilon engine, optional cloud model, voice. */
export default function SettingsPage() {
  const [s, setS] = useState<SystemInfo | null>(null);
  const [phone, setPhone] = useState<{ ready: boolean; webhook_url: string; stt: string | null; tts: string | null } | null>(null);
  useEffect(() => {
    const load = () => {
      api.get<SystemInfo>("/system").then(setS).catch(() => undefined);
      api.get<{ ready: boolean; webhook_url: string; stt: string | null; tts: string | null }>("/telephony/status").then(setPhone).catch(() => undefined);
    };
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);
  const tiers = s?.llm.engine.tiers ?? {};

  return (
    <AppShell title="Settings">
      <div className="mx-auto grid max-w-[1200px] gap-6 lg:grid-cols-2">
        <Card title="Language models" subtitle="Local, through the epsilon engine (llama.cpp CUDA build)">
          <dl className="divide-y divide-border/60">
            <Kv label="Live tier · call brain + Jev">
              {s?.llm.live_ready ? <Pill tone="success">✓ Ready</Pill> : <Pill tone="warning">Loading</Pill>}
            </Kv>
            <Kv label="Model">{tiers.fast?.model ?? "—"}</Kv>
            <Kv label="First-token latency">{s?.llm.latency_ms?.["epsilon:fast:first_token"] != null ? `${s.llm.latency_ms["epsilon:fast:first_token"]} ms` : "—"}</Kv>
            <Kv label="Deep tier · background analysis">
              {tiers.deep?.file_present ? <Pill tone={s?.llm.engine.deep_alive ? "info" : "muted"}>{s?.llm.engine.deep_alive ? "Loaded" : "On demand"}</Pill> : <Pill tone="warning">Model file missing</Pill>}
            </Kv>
            <Kv label="Deep model">{tiers.deep?.model ?? "—"}</Kv>
            <Kv label="Cloud LLM (optional)">{s?.llm.cloud.configured ? <Pill tone="success">{s.llm.cloud.model}</Pill> : <Pill>Not configured</Pill>}</Kv>
            <Kv label="Preference">{s?.llm.prefer === "cloud" ? "Cloud first" : "Local first"}</Kv>
          </dl>
          {s?.llm.engine.error && <p className="mt-3 rounded border border-danger/40 bg-danger/5 p-2 text-xs text-danger">{s.llm.engine.error}</p>}
          <p className="mt-3 text-xs text-text-muted">
            The 27B model does not fit in 4 GB of VRAM, so it runs on CPU/RAM as the deep tier and is only used for post-call analysis. The live call runs on the 4B model on the GPU.
            To use a free cloud model for the live voice instead, set CLOUD_LLM_* in backend/.env.
          </p>
        </Card>

        <Card title="Voice" subtitle="Speech in and out, for the browser and for phone calls">
          <dl className="divide-y divide-border/60">
            <Kv label="Speech recognition">{s ? <Pill tone={s.stt?.provider === "gnani" ? "success" : "muted"}>{s.stt?.provider === "gnani" ? "Gnani real-time (VAD)" : "Browser (Chrome / Edge)"}</Pill> : "—"}</Kv>
            <Kv label="Text-to-speech">{s?.tts.providers?.length ? s.tts.providers.join(" → ") : "browser voice"}</Kv>
            <Kv label="Active voice">{s?.tts.voice ?? "—"}</Kv>
            <Kv label="Fallback voices">{s ? `${s.tts.voice_en}, ${s.tts.voice_hi}` : "—"}</Kv>
            <Kv label="Cached phrases">{s?.tts.cached ?? "—"}</Kv>
            <Kv label="Status">{s ? s.tts.error ? <Pill tone="warning">Degraded: {s.tts.error.slice(0, 40)}</Pill> : <Pill tone="success">✓ Ready</Pill> : "—"}</Kv>
          </dl>
        </Card>

        <Card title="Phone" subtitle="Call the agent from a real phone (Twilio Media Streams, 8 kHz mu-law)">
          <dl className="divide-y divide-border/60">
            <Kv label="Bridge">{phone?.ready ? <Pill tone="success">✓ Ready</Pill> : <Pill tone="warning">Needs a Gnani key</Pill>}</Kv>
            <Kv label="Voice webhook (POST)">{phone?.webhook_url ?? "—"}</Kv>
            <Kv label="Speech recognition">{phone?.stt ?? "—"}</Kv>
            <Kv label="Text-to-speech">{phone?.tts ?? "—"}</Kv>
          </dl>
          <p className="mt-3 text-xs text-text-muted">
            Expose the API with a tunnel (ngrok / cloudflared), set PUBLIC_BASE_URL, and point your Twilio number&apos;s voice webhook at the URL above. The caller is recognised from the last four digits of their number.
          </p>
        </Card>

        <Card title="Simulations" subtitle="Clearly not real integrations">
          <ul className="list-inside list-disc space-y-1 text-[13px] text-text-body">
            <li>Customer, Order, Payment, Refund, Shipping and Account APIs are deterministic mock services.</li>
            <li>Jira / Zoho sync and the Confluence context document are simulated records.</li>
            <li>Learning signals are recorded events; no model is retrained.</li>
          </ul>
        </Card>

        <Card title="Business">
          <dl>
            <Kv label="Product">{s?.product ?? "Resolvyn"}</Kv>
            <Kv label="Demo business">{s?.business ?? "—"}</Kv>
            <Kv label="Voice agent">{s?.agent ?? "—"}</Kv>
            <Kv label="Team consoles connected">{s?.ops_clients ?? "—"}</Kv>
          </dl>
        </Card>
      </div>
    </AppShell>
  );
}
