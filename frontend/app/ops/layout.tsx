import type { ReactNode } from "react";

import { LiveProvider } from "@/lib/live";

export default function OpsLayout({ children }: { children: ReactNode }) {
  return <LiveProvider>{children}</LiveProvider>;
}
