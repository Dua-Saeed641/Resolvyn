import type { TicketStatus } from "@/lib/constants";
import { cx } from "@/lib/utils";

const PIPELINE: TicketStatus[] = [
  "NEW",
  "ANALYZING",
  "ROUTING",
  "ACTIVE",
  "WAITING_FOR_HUMAN",
  "VERIFYING",
  "RESOLVED",
];

/** spec §9: the lifecycle visualized — current stage obvious, completed
 * stages visually distinguishable, FAILED a terminal branch off the line. */
export function TicketStatusPipeline({ status }: { status: TicketStatus }) {
  if (status === "FAILED") {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="rounded border border-danger/30 bg-danger/10 px-2 py-1 font-medium text-danger">FAILED</span>
        <span className="text-text-muted">Terminal failure — did not complete the pipeline</span>
      </div>
    );
  }

  const currentIndex = PIPELINE.indexOf(status);

  return (
    <div className="flex items-center overflow-x-auto text-xs">
      {PIPELINE.map((step, i) => {
        const isCurrent = i === currentIndex;
        const isDone = i < currentIndex;
        return (
          <div key={step} className="flex items-center">
            <span
              className={cx(
                "whitespace-nowrap rounded px-2 py-1 font-medium",
                isCurrent && "bg-text-primary text-bg-primary",
                isDone && "text-success",
                !isCurrent && !isDone && "text-text-muted"
              )}
            >
              {step.replaceAll("_", " ")}
            </span>
            {i < PIPELINE.length - 1 && <span className="mx-1 text-text-muted">→</span>}
          </div>
        );
      })}
    </div>
  );
}
