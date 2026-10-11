import type { ReactNode } from "react";
import { cx } from "../../lib/cx";
import { owaspShort, severityLabel, statusLabel } from "../../lib/domain";

type Tone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info";

interface BadgeProps {
  tone?: Tone;
  outline?: boolean;
  mono?: boolean;
  className?: string;
  title?: string;
  children: ReactNode;
}

export default function Badge({
  tone = "neutral",
  outline = false,
  mono = false,
  className,
  title,
  children,
}: BadgeProps) {
  return (
    <span
      title={title}
      className={cx(
        "badge",
        tone !== "neutral" && `badge--${tone}`,
        outline && "badge--outline",
        mono && "badge--mono",
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Severity chip: carries the same colour language as the exported reports. */
export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <Badge tone={severity as Tone} className="badge--severity">
      {severityLabel(severity)}
    </Badge>
  );
}

/** Scan status pill with an animated dot while the scan is running. */
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cx("status-pill", `status-pill--${status}`)}>
      <span className="status-pill__dot" aria-hidden="true" />
      {statusLabel(status)}
    </span>
  );
}

/** HTTP method tag for endpoint rows. */
export function MethodBadge({ method }: { method: string }) {
  const normalised = method.toLowerCase();
  return (
    <span className={cx("method", `method--${normalised}`)}>
      {method.toUpperCase()}
    </span>
  );
}

/** OWASP API Top 10 (2023) category tag. */
export function OwaspBadge({ category }: { category: string }) {
  return (
    <Badge tone="accent" mono title={category}>
      {owaspShort(category)}
    </Badge>
  );
}
