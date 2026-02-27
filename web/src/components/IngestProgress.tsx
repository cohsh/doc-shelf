import type { TaskStatusValue } from "../types/document";

interface Props {
  status: TaskStatusValue;
  message: string;
}

const STEPS: { key: TaskStatusValue; label: string }[] = [
  { key: "extracting", label: "Extracting text from PDF" },
  { key: "saving", label: "Saving document" },
  { key: "completed", label: "Done" },
];

const ORDER: TaskStatusValue[] = [
  "pending",
  "extracting",
  "saving",
  "completed",
  "failed",
];

export default function IngestProgress({ status, message }: Props) {
  const currentIdx = ORDER.indexOf(status);
  const failed = status === "failed";

  return (
    <div className="progress-steps">
      {STEPS.map((step, i) => {
        const stepIdx = ORDER.indexOf(step.key);
        const completed = !failed && currentIdx > stepIdx;
        const active = !failed && step.key === status;
        const stepClass = completed ? "completed" : active ? "active" : "";

        return (
          <div key={step.key} className={`progress-step ${stepClass}`}>
            <div className={`step-icon ${stepClass}`}>
              {completed ? "\u2713" : i + 1}
            </div>
            <span>{step.label}</span>
          </div>
        );
      })}

      {failed && (
        <div className="progress-step failed" style={{ marginTop: 8, fontWeight: 500 }}>
          Error: {message}
        </div>
      )}
    </div>
  );
}
