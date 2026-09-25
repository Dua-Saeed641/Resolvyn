import { Brain, Ear, GraduationCap, ShieldCheck } from "lucide-react";

const STEPS = [
  { icon: Ear, title: "Understands", text: "Language, order IDs, mood and who is speaking, judged in about 13 ms, before any model runs." },
  { icon: Brain, title: "Remembers", text: "Your policies and every solved case, in a vector index and a knowledge graph, by department." },
  { icon: ShieldCheck, title: "Acts and verifies", text: "Runs the real tools. Says a refund is done only after the refund service confirms it." },
  { icon: GraduationCap, title: "Learns", text: "A new problem goes to a person who teaches it. The next customer gets the answer at once." },
];

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-[1240px] scroll-mt-20 px-6 py-20">
      <div className="max-w-2xl">
        <p className="text-sm font-medium text-success">How it works</p>
        <h2 className="mt-3 font-display text-3xl font-normal tracking-tight sm:text-5xl">Every answer is checked before it is said.</h2>
      </div>
      <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s, i) => (
          <li key={s.title} className="group relative overflow-hidden rounded-2xl border bg-card p-6 transition-shadow hover:shadow-float">
            <span className="font-display text-sm text-muted-foreground">0{i + 1}</span>
            <span className="mt-5 flex h-11 w-11 items-center justify-center rounded-xl bg-brand/12 text-success ring-1 ring-brand/25 transition-colors group-hover:bg-brand group-hover:text-brand-foreground">
              <s.icon className="h-5 w-5" />
            </span>
            <h3 className="mt-5 font-display text-xl font-normal">{s.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
