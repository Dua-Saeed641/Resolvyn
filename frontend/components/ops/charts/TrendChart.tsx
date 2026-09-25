"use client";

import { useMemo, useState } from "react";

const W = 600;
const H = 160;
const PAD = { top: 12, right: 12, bottom: 22, left: 28 };

function niceMax(v: number): number {
  if (v <= 4) return 4;
  const step = Math.pow(10, Math.floor(Math.log10(v)));
  const n = Math.ceil(v / step);
  const rounded = n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return rounded * step;
}

/** A single-series trend line (rolling ticket volume) — one hue needs no legend
 *  box (the card title already says what's plotted); a hover crosshair+tooltip
 *  ships by default on any line/area, per the dataviz skill, since labeling
 *  every one of 24 points directly would be unreadable. */
export function TrendChart({ data }: { data: { label: string; count: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const n = data.length;

  const max = useMemo(() => niceMax(Math.max(...data.map((d) => d.count), 0)), [data]);
  const x = (i: number) => PAD.left + (n <= 1 ? 0 : (i / (n - 1)) * innerW);
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;

  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.count).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${x(n - 1).toFixed(1)} ${PAD.top + innerH} L ${x(0).toFixed(1)} ${PAD.top + innerH} Z`;

  const gridSteps = [0, 0.5, 1];
  const total = data.reduce((s, d) => s + d.count, 0);
  const last = data[n - 1];

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.left) / innerW) * (n - 1));
    setHover(Math.min(n - 1, Math.max(0, i)));
  };

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-[11px] text-text-muted">Last 24 hours · {total} tickets created</p>
        {last && <p className="text-[13px] tabular-nums text-text-primary">{last.count} this hour</p>}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Ticket volume over the last 24 hours">
        {gridSteps.map((g) => (
          <line key={g} x1={PAD.left} x2={W - PAD.right} y1={y(max * g)} y2={y(max * g)} stroke="currentColor" strokeWidth={1} className="text-border" />
        ))}
        {gridSteps.map((g) => (
          <text key={g} x={PAD.left - 6} y={y(max * g)} textAnchor="end" dominantBaseline="middle" className="fill-text-secondary text-[9px]">
            {Math.round(max * g)}
          </text>
        ))}
        <path d={areaPath} className="fill-brand" fillOpacity={0.14} stroke="none" />
        <path d={linePath} className="stroke-brand" strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
        {hover !== null && (
          <>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + innerH} className="stroke-text-secondary" strokeWidth={1} />
            <circle cx={x(hover)} cy={y(data[hover].count)} r={4} className="fill-brand stroke-card" strokeWidth={2} />
          </>
        )}
        {/* x-axis: every 4th hour label to avoid crowding */}
        {data.map((d, i) =>
          i % 4 === 0 ? (
            <text key={i} x={x(i)} y={H - 4} textAnchor="middle" className="fill-text-secondary text-[9px]">
              {d.label}
            </text>
          ) : null,
        )}
        <rect x={PAD.left} y={PAD.top} width={innerW} height={innerH} fill="transparent" onMouseMove={onMove} onMouseLeave={() => setHover(null)} />
      </svg>
      {hover !== null && (
        <div className="mt-1 text-center text-[11px] text-text-muted">
          {data[hover].label} · <span className="text-text-primary">{data[hover].count} ticket{data[hover].count === 1 ? "" : "s"}</span>
        </div>
      )}
    </div>
  );
}
