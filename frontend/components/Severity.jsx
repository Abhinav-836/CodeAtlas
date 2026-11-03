import { normalizeLevel } from "@/lib/format";

// Map-legend symbols: shape + colour, so severity never relies on colour alone.
export function SeverityMark({ level, className = "" }) {
  const l = normalizeLevel(level);
  const common = `inline-block shrink-0 ${className}`;
  switch (l) {
    case "critical":
      return <span aria-hidden="true" className={`${common} h-2.5 w-2.5 rotate-45 bg-critical`} />;
    case "high":
      return (
        <span
          aria-hidden="true"
          className={`${common} h-0 w-0 border-x-[6px] border-b-[10px] border-x-transparent border-b-high`}
        />
      );
    case "medium":
      return <span aria-hidden="true" className={`${common} h-3 w-3 rounded-full border-2 border-medium`} />;
    case "low":
      return <span aria-hidden="true" className={`${common} h-2.5 w-2.5 rounded-full bg-low`} />;
    default:
      return <span aria-hidden="true" className={`${common} h-0.5 w-3 bg-none`} />;
  }
}

const TEXT = {
  critical: "text-critical",
  high: "text-high",
  medium: "text-medium",
  low: "text-low",
  none: "text-none",
};

export function SeverityLabel({ level, children }) {
  const l = normalizeLevel(level);
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${TEXT[l]}`}>
      <SeverityMark level={l} />
      {children ?? (l === "none" ? "No risk" : l[0].toUpperCase() + l.slice(1))}
    </span>
  );
}

export const severityText = (level) => TEXT[normalizeLevel(level)];