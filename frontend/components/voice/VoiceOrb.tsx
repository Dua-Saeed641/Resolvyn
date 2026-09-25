"use client";

import { useEffect, useRef } from "react";

export type OrbState = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "muted";

/**
 * The voice assistant on screen: a soft, organic orb drawn on a canvas that changes behaviour with what Riya is doing.
 *   idle / muted   slow breathing, almost still
 *   connecting     a ring drawing around the orb
 *   listening      gentle, wide ripples that respond to being spoken to
 *   thinking       the orb tightens and a bright arc orbits it
 *   speaking       the shape ripples with the rhythm of speech
 * Colours come from the theme tokens (neutral foreground with a restrained blue accent), so it works in light and dark.
 */
export function VoiceOrb({ state, size = 280, level = 0 }: { state: OrbState; size?: number; level?: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const live = useRef({ state, level });
  live.current = { state, level };

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    el.width = size * dpr;
    el.height = size * dpr;
    ctx.scale(dpr, dpr);

    const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let colors = { fg: css("--foreground"), accent: css("--info") };
    const themeWatch = new MutationObserver(() => (colors = { fg: css("--foreground"), accent: css("--info") }));
    themeWatch.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    let amp = 0.03; // how much the outline moves
    let radius = 0.5; // orb radius as a share of the canvas half-size
    let speech = 0; // organic "voice energy" while speaking
    let raf = 0;
    const start = performance.now();
    const c = size / 2;

    const noise = (a: number, t: number, seed: number) =>
      Math.sin(a * 2 + t * 1.1 + seed) * 0.5 + Math.sin(a * 3 - t * 0.8 + seed * 2.1) * 0.3 + Math.sin(a * 5 + t * 1.9 + seed * 0.7) * 0.2;

    const blob = (r: number, a: number, t: number, seed: number) => {
      ctx.beginPath();
      const n = 90;
      for (let i = 0; i <= n; i++) {
        const ang = (i / n) * Math.PI * 2;
        const rr = r * (1 + a * noise(ang, t, seed));
        const x = c + Math.cos(ang) * rr;
        const y = c + Math.sin(ang) * rr;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
    };

    const frame = (now: number) => {
      const t = reduce ? 0 : (now - start) / 1000;
      const { state: st, level: lvl } = live.current;
      const targetAmp = { idle: 0.035, muted: 0.02, connecting: 0.05, listening: 0.09, thinking: 0.05, speaking: 0.13 }[st];
      const targetR = { idle: 0.46, muted: 0.44, connecting: 0.46, listening: 0.5, thinking: 0.42, speaking: 0.52 }[st];
      // speech energy: an irregular envelope (syllables) rather than a metronome
      const syll = 0.5 + 0.5 * Math.sin(t * 7.3) * Math.sin(t * 2.9 + 1.3) + 0.25 * Math.sin(t * 13.1);
      const targetSpeech = st === "speaking" ? Math.max(0.15, Math.min(1, syll)) : 0;
      speech += (targetSpeech - speech) * 0.12;
      amp += (targetAmp + speech * 0.16 + lvl * 0.2 - amp) * 0.08;
      radius += (targetR + speech * 0.05 - radius) * 0.08;

      ctx.clearRect(0, 0, size, size);
      const R = c * radius * 1.12;

      // soft outer glow
      const glowR = Math.min(R * 1.7, c * 0.99);
      const glow = ctx.createRadialGradient(c, c, R * 0.6, c, c, glowR);
      glow.addColorStop(0, `hsl(${colors.accent} / ${0.16 + speech * 0.12})`);
      glow.addColorStop(1, `hsl(${colors.accent} / 0)`);
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(c, c, glowR, 0, Math.PI * 2);
      ctx.fill();

      // three translucent layers give the orb depth
      const layers: [number, number, number, number][] = [
        [1.0, 1.0, 0, 0.08],
        [0.9, 1.25, 2.1, 0.1],
        [0.78, 1.55, 4.3, 0.14],
      ];
      for (const [scale, ampMul, seed, alpha] of layers) {
        blob(R * scale, amp * ampMul, t, seed);
        ctx.fillStyle = `hsl(${colors.fg} / ${alpha + speech * 0.03})`;
        ctx.fill();
        ctx.lineWidth = 1;
        ctx.strokeStyle = `hsl(${colors.fg} / ${alpha * 1.6})`;
        ctx.stroke();
      }

      // core: a clean disc with a light-to-dark gradient
      const core = ctx.createRadialGradient(c - R * 0.25, c - R * 0.3, R * 0.05, c, c, R * 0.72);
      core.addColorStop(0, `hsl(${colors.accent} / 0.55)`);
      core.addColorStop(0.55, `hsl(${colors.fg} / 0.55)`);
      core.addColorStop(1, `hsl(${colors.fg} / 0.85)`);
      blob(R * 0.62, amp * 0.6, t * 1.2, 7.7);
      ctx.fillStyle = core;
      ctx.fill();

      // listening: ripples move outward
      if (st === "listening") {
        for (let k = 0; k < 3; k++) {
          const p = ((t * 0.45 + k / 3) % 1);
          ctx.beginPath();
          ctx.arc(c, c, R * (0.9 + p * 0.55), 0, Math.PI * 2);
          ctx.strokeStyle = `hsl(${colors.fg} / ${0.16 * (1 - p)})`;
          ctx.lineWidth = 1.25;
          ctx.stroke();
        }
      }
      // thinking: a bright arc orbits the orb
      if (st === "thinking") {
        const a0 = t * 2.4;
        ctx.beginPath();
        ctx.arc(c, c, R * 1.12, a0, a0 + Math.PI * 0.55);
        ctx.strokeStyle = `hsl(${colors.accent} / 0.9)`;
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.stroke();
      }
      // connecting: a ring draws itself
      if (st === "connecting") {
        const a0 = -Math.PI / 2;
        const sweep = ((t * 0.9) % 1) * Math.PI * 2;
        ctx.beginPath();
        ctx.arc(c, c, R * 1.12, a0, a0 + sweep);
        ctx.strokeStyle = `hsl(${colors.accent} / 0.8)`;
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.stroke();
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      themeWatch.disconnect();
    };
  }, [size]);

  return <canvas ref={canvas} style={{ width: size, height: size }} aria-hidden />;
}
