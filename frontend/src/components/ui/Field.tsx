import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useId, useState } from "react";
import { cx } from "../../lib/cx";
import Icon from "../Icon";

interface FieldProps {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  children: (ids: { id: string; invalid: boolean }) => ReactNode;
}

/**
 * Label + control + hint/error wrapper. The control is supplied through a
 * render prop so each input type can attach the generated ids itself.
 */
export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  const invalid = error !== null && error !== undefined;
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        <span>{label}</span>
        {hint !== undefined && <span className="field__hint">{hint}</span>}
      </label>
      {children({ id, invalid })}
      {invalid && <span className="field__error">{error}</span>}
    </div>
  );
}

export function TextInput({
  className,
  invalid = false,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      {...rest}
      className={cx("input", className)}
      aria-invalid={invalid || undefined}
    />
  );
}

export function PasswordInput({
  className,
  invalid = false,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="input-group">
      <input
        {...rest}
        type={visible ? "text" : "password"}
        className={cx("input", className)}
        aria-invalid={invalid || undefined}
      />
      <button
        type="button"
        className="input-group__action"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide value" : "Show value"}
        title={visible ? "Hide value" : "Show value"}
      >
        <Icon name={visible ? "eye-off" : "eye"} size={16} />
      </button>
    </div>
  );
}

export function SelectInput({
  className,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...rest} className={cx("select", className)}>
      {children}
    </select>
  );
}

export function TextArea({
  className,
  invalid = false,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }) {
  return (
    <textarea
      {...rest}
      className={cx("textarea", className)}
      aria-invalid={invalid || undefined}
    />
  );
}
