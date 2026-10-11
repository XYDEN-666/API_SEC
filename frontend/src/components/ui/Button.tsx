import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../../lib/cx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  block?: boolean;
  iconOnly?: boolean;
}

export default function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  icon,
  block = false,
  iconOnly = false,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      className={cx(
        "btn",
        `btn--${variant}`,
        size === "sm" && "btn--sm",
        block && "btn--block",
        iconOnly && "btn--icon",
        className,
      )}
      disabled={disabled ?? loading}
    >
      {loading ? <span className="btn__spinner" aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}
