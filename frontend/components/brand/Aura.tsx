import { cn } from "@/lib/utils";

/** The banner's soft blurred green light, as a background layer. Place inside a `relative overflow-hidden` parent. */
export function Aura({ className, strength = 1 }: { className?: string; strength?: number }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)} style={{ opacity: strength }}>
      <div className="absolute -left-40 -top-40 h-[520px] w-[520px] animate-drift rounded-full bg-brand/25 blur-[110px] dark:bg-brand/15" />
      <div className="absolute -bottom-52 -right-40 h-[620px] w-[620px] animate-drift rounded-full bg-brand/30 blur-[130px] [animation-delay:-9s] dark:bg-brand/15" />
    </div>
  );
}
