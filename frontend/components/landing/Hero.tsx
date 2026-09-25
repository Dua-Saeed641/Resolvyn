import { ArrowRight, Check, Mail, Phone } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Aura } from "@/components/brand/Aura";
import { Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";

const STATS = [
  { value: "~10 ms", label: "to the first acknowledgement" },
  { value: "100%", label: "of actions verified before they are said" },
  { value: "3", label: "channels: voice, chat, email" },
];

function Equalizer() {
  return (
    <div className="flex h-5 items-end gap-[3px]" aria-hidden>
      {[0.5, 0.9, 0.6, 1, 0.7, 0.4].map((h, i) => (
        <span key={i} className="w-[3px] origin-bottom animate-eq rounded-full bg-brand" style={{ height: `${h * 100}%`, animationDelay: `${i * 120}ms` }} />
      ))}
    </div>
  );
}

/** The landing hero of the customer side: the promise, two ways in, proof, and the brand's human in soft green light. */
export function Hero() {
  return (
    <section className="grain relative isolate overflow-hidden bg-background">
      <Aura />

      <header className="relative z-20 mx-auto flex h-16 max-w-[1240px] items-center justify-between px-6">
        <Link href="/" aria-label="Resolvyn home">
          <Logo size={34} />
        </Link>
        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex" aria-label="Sections">
          <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
          <a href="#talk" className="transition-colors hover:text-foreground">Talk to Riya</a>
          <Link href="/ops" className="transition-colors hover:text-foreground">Team console</Link>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild className="hidden rounded-full sm:inline-flex">
            <a href="#talk">Start now</a>
          </Button>
        </div>
      </header>

      <div className="relative mx-auto grid max-w-[1240px] items-center gap-6 px-6 pb-16 pt-8 lg:grid-cols-[1.08fr_0.92fr] lg:pb-24 lg:pt-12">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-brand/30 bg-brand/10 px-3 py-1 text-xs font-medium text-success">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-brand" />
            </span>
            Autonomous customer support
          </span>

          <h1 className="mt-6 font-display text-[44px] font-normal leading-[1.02] tracking-tight text-foreground sm:text-6xl lg:text-[76px]">
            Support that
            <br />
            <span className="relative inline-block">
              <span className="relative z-10">resolves</span>
              <span className="absolute -bottom-1 left-0 right-0 z-0 h-3 rounded-full bg-brand/35 blur-[2px]" aria-hidden />
            </span>{" "}
            it.
          </h1>

          <p className="mt-6 max-w-[520px] text-lg leading-relaxed text-muted-foreground">
            Riya checks your order, fixes the problem, proves it worked, and brings in a person the moment one is needed. By voice, chat or email, in English or Hindi.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg" className="h-12 rounded-full px-7 text-[15px]">
              <a href="#talk">
                <Phone /> Talk to Riya
              </a>
            </Button>
            <Button asChild size="lg" variant="outline" className="h-12 rounded-full px-7 text-[15px]">
              <a href="#talk">
                <Mail /> Write an email <ArrowRight />
              </a>
            </Button>
          </div>

          <dl className="mt-12 grid max-w-[560px] grid-cols-3 gap-6 border-t pt-6">
            {STATS.map((s) => (
              <div key={s.value}>
                <dt className="font-display text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">{s.value}</dt>
                <dd className="mt-1 text-xs leading-snug text-muted-foreground">{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="relative mx-auto h-[520px] w-full max-w-[500px] sm:h-[620px] lg:h-[680px]">
          <Image
            src="/hero-human.png"
            alt="A soft, blurred human silhouette in green light"
            width={736}
            height={1104}
            priority
            className="absolute inset-x-0 bottom-0 mx-auto h-full w-auto max-w-none object-contain [mask-image:linear-gradient(to_bottom,black_78%,transparent)]"
          />

          <div className="absolute right-0 top-10 animate-float rounded-2xl border bg-card/95 p-3.5 shadow-float sm:right-[-8px]">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary font-display text-sm text-primary-foreground">R</span>
              <div>
                <p className="text-sm font-semibold leading-tight">Riya</p>
                <p className="text-xs text-muted-foreground">Listening</p>
              </div>
              <Equalizer />
            </div>
          </div>

          <div className="absolute left-[-6px] top-[44%] max-w-[250px] animate-float rounded-2xl border bg-card/95 p-3.5 shadow-float [animation-delay:-2.5s] sm:left-[-28px]">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-brand-foreground">
                <Check className="h-4 w-4" strokeWidth={3} />
              </span>
              <div>
                <p className="text-sm font-semibold leading-tight">Refund of ₹2,499</p>
                <p className="mt-1 text-xs leading-snug text-muted-foreground">Verified with the refund service before Riya said it was done.</p>
              </div>
            </div>
          </div>

          <div className="absolute bottom-16 right-2 animate-float rounded-2xl border bg-card/95 p-3.5 shadow-float [animation-delay:-5s] sm:right-[-4px]">
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Ticket PH-1042</p>
            <p className="mt-0.5 font-display text-lg">Resolved in 41 s</p>
            <div className="mt-2 flex gap-1" aria-hidden>
              {[0, 1, 2, 3, 4].map((i) => (
                <span key={i} className="h-1 w-8 rounded-full bg-brand" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
