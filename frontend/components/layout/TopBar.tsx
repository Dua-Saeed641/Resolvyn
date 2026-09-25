"use client";

import { Cpu, Radio } from "lucide-react";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Badge } from "@/components/ui/badge";
import { useLive } from "@/lib/live";

/** Page title on the left; live calls, the language model and the connection on the right. */
export function TopBar({ title }: { title: string }) {
  const { connected, llm, stats } = useLive();
  const ready = llm?.live_ready;
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card/80 px-6 backdrop-blur">
      <h1 className="text-[17px] tracking-tight text-foreground">{title}</h1>
      <div className="flex items-center gap-2.5">
        {stats ? (
          <Badge variant={stats.live_calls > 0 ? "info" : "muted"}>
            <Radio className="h-3 w-3" />
            {stats.live_calls} live call{stats.live_calls === 1 ? "" : "s"}
          </Badge>
        ) : null}
        {llm ? (
          <Badge variant={ready ? "success" : "warning"} title="Qwen through the epsilon engine, on this machine">
            <Cpu className="h-3 w-3" />
            {ready ? "Model ready" : "Model loading"}
          </Badge>
        ) : null}
        <Badge variant={connected ? "success" : "danger"}>
          <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
          {connected ? "Operational" : "Reconnecting"}
        </Badge>
        <ThemeToggle />
      </div>
    </header>
  );
}
