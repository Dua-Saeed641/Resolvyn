import Image from "next/image";

import { cn } from "@/lib/utils";

/** The Resolvyn mark (public/resolvyn-logo.png). Use this everywhere the brand appears. */
export function LogoMark({ size = 32, className }: { size?: number; className?: string }) {
  return <Image src="/resolvyn-logo.png" alt="Resolvyn" width={size} height={size} priority className={cn("shrink-0 select-none", className)} />;
}

/** Mark plus wordmark, with an optional second line. */
export function Logo({ size = 32, subtitle, className }: { size?: number; subtitle?: string; className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <LogoMark size={size} />
      <span>
        <span className="block font-display text-[17px] font-normal leading-tight tracking-tight text-foreground">Resolvyn</span>
        {subtitle && <span className="block text-[11px] leading-tight text-muted-foreground">{subtitle}</span>}
      </span>
    </span>
  );
}
