"use client";

import { Keyboard, Mic, MicOff, PhoneOff, Send, MessageSquare, Phone } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VoiceOrb, type OrbState } from "@/components/voice/VoiceOrb";
import type { CustomerProfile } from "@/features/types";
import type { AgentStatus, CallStatus, Line } from "@/lib/useCall";
import { cn } from "@/lib/utils";

const GUEST = "guest";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

function useTimer(active: boolean) {
  const [s, setS] = useState(0);
  useEffect(() => {
    if (!active) return setS(0);
    const t = setInterval(() => setS((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [active]);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Start, run and finish a call or chat with Riya. During a voice call the screen is the assistant itself: an animated orb,
 *  live captions of both sides, and three controls. */
export function CallPanel(props: {
  customers: CustomerProfile[];
  status: CallStatus;
  agentStatus: AgentStatus;
  lines: Line[];
  interim: string;
  error: string | null;
  muted: boolean;
  sttSupported: boolean;
  ttsFallback: boolean;
  sttMode: "server" | "browser" | "none";
  customerId: string;
  onCustomer: (id: string) => void;
  onStart: (o: { customerId?: string; mode: "voice" | "chat"; lang: "en" | "hi" }) => void;
  onSend: (t: string) => void;
  onEnd: () => void;
  onMute: () => void;
  onReset: () => void;
  agentName: string;
}) {
  const { status, agentStatus, lines, interim, error, muted, sttSupported, ttsFallback, sttMode, customerId, customers } = props;
  const [mode, setMode] = useState<"voice" | "chat">("voice");
  const [callMode, setCallMode] = useState<"voice" | "chat">("voice"); // what the running session is
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [text, setText] = useState("");
  const [showTranscript, setShowTranscript] = useState(false);
  const [typing, setTyping] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const live = status === "live" || status === "connecting";
  const clock = useTimer(status === "live");

  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [lines.length, interim, showTranscript]);
  useEffect(() => {
    if (!sttSupported) setMode("chat");
  }, [sttSupported]);

  const me = customers.find((c) => c.customer_id === customerId);
  const orbState: OrbState = status === "connecting" ? "connecting" : muted && agentStatus === "listening" ? "muted" : agentStatus;
  const lastAgent = [...lines].reverse().find((l) => l.who === "agent" || l.who === "human");
  const caption = interim || (agentStatus === "thinking" ? "" : lastAgent?.text ?? "");
  const captionFrom = interim ? "you" : lastAgent?.who === "human" ? "human" : "agent";
  const statusText = status === "connecting" ? "Connecting…" : muted && agentStatus === "listening" ? "Microphone muted" : { listening: "Listening", thinking: "Thinking", speaking: "Riya is speaking" }[agentStatus];

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    props.onSend(text);
    setText("");
  };

  // ── before the call ───────────────────────────────────────────────────────
  if (!live && status !== "ended") {
    return (
      <Card className="overflow-hidden" aria-label="Talk to support">
        <div className="flex flex-col items-center border-b bg-muted/30 px-6 pb-2 pt-8">
          <VoiceOrb state="idle" size={200} />
          <h2 className="-mt-2 text-lg font-semibold tracking-tight">Talk to {props.agentName}</h2>
          <p className="mb-5 mt-1 max-w-sm text-center text-sm text-muted-foreground">
            She can look up your orders and payments, fix what she can on the spot, and bring in a teammate the moment she needs one.
          </p>
        </div>
        <div className="space-y-5 p-6">
          <div className="space-y-2">
            <Label htmlFor="who">Contact us as</Label>
            <Select value={customerId || GUEST} onValueChange={(v) => props.onCustomer(v === GUEST ? "" : v)}>
              <SelectTrigger id="who">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.customer_id} value={c.customer_id}>
                    {c.name} · {c.plan}
                  </SelectItem>
                ))}
                <SelectItem value={GUEST}>Guest (Riya will ask who you are)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Channel</Label>
              <Tabs value={mode} onValueChange={(v) => setMode(v as "voice" | "chat")}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="voice" disabled={!sttSupported} className="gap-1.5">
                    <Phone className="h-3.5 w-3.5" /> Voice
                  </TabsTrigger>
                  <TabsTrigger value="chat" className="gap-1.5">
                    <MessageSquare className="h-3.5 w-3.5" /> Chat
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            <div className="space-y-2">
              <Label>Language</Label>
              <Tabs value={lang} onValueChange={(v) => setLang(v as "en" | "hi")}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="en">English</TabsTrigger>
                  <TabsTrigger value="hi">हिन्दी</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>

          {!sttSupported && <p className="text-xs text-warning">Voice calls need Chrome or Edge. Chat works in any browser.</p>}
          {error && (
            <p role="alert" className="text-xs text-danger">
              {error}
            </p>
          )}
          <Button
            size="lg"
            className="w-full"
            onClick={() => {
              setCallMode(mode);
              props.onStart({ customerId: customerId || undefined, mode, lang });
            }}
          >
            {mode === "voice" ? <Phone /> : <MessageSquare />}
            {mode === "voice" ? `Call ${props.agentName}` : "Start chat"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Use headphones for the best voice experience. Speak naturally; you can interrupt at any time. We email you a summary after every call or chat.
          </p>
        </div>
      </Card>
    );
  }

  // ── after the call ────────────────────────────────────────────────────────
  if (status === "ended") {
    return (
      <Card className="p-6" aria-label="Call ended">
        <div className="flex flex-col items-center text-center">
          <VoiceOrb state="idle" size={140} />
          <h2 className="-mt-1 text-lg font-semibold tracking-tight">The call has ended</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Your ticket stays open on the right and updates in real time. We are emailing you a summary{me?.email ? ` at ${me.email}` : ""}.
          </p>
          <Button className="mt-5" onClick={props.onReset}>
            New conversation
          </Button>
        </div>
        {lines.length > 0 && (
          <div className="mt-6 max-h-64 space-y-2 overflow-y-auto border-t pt-4">
            <Transcript lines={lines} interim="" />
          </div>
        )}
      </Card>
    );
  }

  // ── a chat ────────────────────────────────────────────────────────────────
  if (callMode === "chat") {
    return (
      <Card className="flex h-[640px] flex-col overflow-hidden" aria-label="Chat with support">
        <Header name={props.agentName} me={me?.name} right={<Badge variant="success">Online</Badge>} />
        <div className="flex-1 space-y-2.5 overflow-y-auto px-5 py-4" aria-live="polite">
          <Transcript lines={lines} interim={interim} />
          {agentStatus === "thinking" && <Badge variant="muted">Riya is typing…</Badge>}
          <div ref={end} />
        </div>
        <div className="border-t p-3">
          {error && (
            <p role="alert" className="mb-2 text-xs text-danger">
              {error}
            </p>
          )}
          <form className="flex items-center gap-2" onSubmit={submit}>
            <Input placeholder="Type your message…" value={text} onChange={(e) => setText(e.target.value)} aria-label="Message" />
            <Button type="submit" size="icon" disabled={!text.trim()} aria-label="Send">
              <Send />
            </Button>
            <Button type="button" variant="outline" onClick={props.onEnd}>
              End chat
            </Button>
          </form>
        </div>
      </Card>
    );
  }

  // ── a voice call: the assistant ───────────────────────────────────────────
  return (
    <Card className="flex min-h-[640px] flex-col overflow-hidden" aria-label="Voice call with support">
      <Header
        name={props.agentName}
        me={me?.name}
        right={
          <div className="flex items-center gap-2">
            <Badge variant="muted" className="tabular-nums">
              {clock}
            </Badge>
            <Badge variant={status === "connecting" ? "warning" : "success"}>{status === "connecting" ? "Connecting" : "Live"}</Badge>
          </div>
        }
      />
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-4">
        <VoiceOrb state={orbState} size={300} />
        <p className="-mt-3 text-sm font-medium text-foreground" role="status" aria-live="polite">
          {statusText}
        </p>
        <div className="mt-3 flex min-h-[84px] max-w-md items-start justify-center text-center">
          {caption ? (
            <p
              key={caption}
              className={cn(
                "animate-fade-in text-[15px] leading-relaxed",
                captionFrom === "you" ? "italic text-muted-foreground" : captionFrom === "human" ? "text-info" : "text-foreground",
              )}
            >
              {captionFrom === "human" && <span className="mb-0.5 block text-[11px] font-medium uppercase tracking-wide">Team member</span>}
              {caption}
              {captionFrom === "you" ? "…" : ""}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">{status === "connecting" ? "One moment…" : "Go ahead, I am listening."}</p>
          )}
        </div>
      </div>

      {(typing || showTranscript) && (
        <div className="border-t px-5 py-3">
          {showTranscript && (
            <div className="mb-3 max-h-48 space-y-2 overflow-y-auto">
              <Transcript lines={lines} interim={interim} />
              <div ref={end} />
            </div>
          )}
          {typing && (
            <form className="flex items-center gap-2" onSubmit={submit}>
              <Input autoFocus placeholder="Or type here…" value={text} onChange={(e) => setText(e.target.value)} aria-label="Message" />
              <Button type="submit" size="icon" disabled={!text.trim()} aria-label="Send">
                <Send />
              </Button>
            </form>
          )}
        </div>
      )}

      <div className="flex flex-col items-center gap-3 border-t bg-muted/30 px-5 py-4">
        {error && (
          <p role="alert" className="text-xs text-danger">
            {error}
          </p>
        )}
        <div className="flex items-center gap-3">
          <Button variant={muted ? "secondary" : "outline"} size="icon" className="h-12 w-12 rounded-full" onClick={props.onMute} aria-pressed={muted} aria-label={muted ? "Unmute microphone" : "Mute microphone"}>
            {muted ? <MicOff /> : <Mic />}
          </Button>
          <Button variant="destructive" size="icon" className="h-14 w-14 rounded-full" onClick={props.onEnd} aria-label="End call">
            <PhoneOff className="!size-5" />
          </Button>
          <Button variant={typing ? "secondary" : "outline"} size="icon" className="h-12 w-12 rounded-full" onClick={() => setTyping((v) => !v)} aria-pressed={typing} aria-label="Type instead">
            <Keyboard />
          </Button>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <button className="underline-offset-2 hover:text-foreground hover:underline" onClick={() => setShowTranscript((v) => !v)}>
            {showTranscript ? "Hide transcript" : "Show transcript"}
          </button>
          <span aria-hidden>·</span>
          <span>{sttMode === "server" ? "Gnani real-time speech" : sttMode === "browser" ? "Browser speech recognition" : "Voice"}{ttsFallback ? " · fallback voice" : ""}</span>
        </div>
      </div>
    </Card>
  );
}

function Header({ name, me, right }: { name: string; me?: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b px-5 py-3.5">
      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarFallback className="bg-primary text-primary-foreground">{name[0]}</AvatarFallback>
        </Avatar>
        <div>
          <p className="text-sm font-semibold leading-tight">{name}</p>
          <p className="text-xs text-muted-foreground">{me ? `Helping ${me}` : "Nova Retail support"}</p>
        </div>
      </div>
      {right}
    </div>
  );
}

function Transcript({ lines, interim }: { lines: Line[]; interim: string }) {
  return (
    <>
      {lines.map((l) => {
        const mine = l.who === "you" || l.who === "side";
        return (
          <div key={l.id} className={cn("animate-fade-in flex", mine ? "justify-end" : "justify-start")}>
            <p
              className={cn(
                "max-w-[85%] rounded-2xl px-3.5 py-2 text-[13px] leading-relaxed",
                l.who === "you" && "rounded-br-md bg-primary text-primary-foreground",
                l.who === "agent" && "rounded-bl-md bg-muted text-foreground",
                l.who === "human" && "rounded-bl-md border border-info/30 bg-info/10 text-foreground",
                l.who === "side" && "border border-dashed bg-transparent italic text-muted-foreground",
              )}
            >
              {l.who === "human" && <span className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-info">Team member</span>}
              {l.who === "side" && <span className="mb-0.5 block text-[10px] font-medium uppercase not-italic tracking-wide">Talking to someone else · Riya stays quiet</span>}
              {l.text}
            </p>
          </div>
        );
      })}
      {interim && (
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-2xl rounded-br-md border border-dashed px-3.5 py-2 text-[13px] italic text-muted-foreground">{interim}…</p>
        </div>
      )}
    </>
  );
}
