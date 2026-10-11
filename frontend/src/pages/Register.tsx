import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AuthLayout from "../components/AuthLayout";
import Icon from "../components/Icon";
import Button from "../components/ui/Button";
import { ErrorAlert } from "../components/ui/Feedback";
import { Field, PasswordInput, TextInput } from "../components/ui/Field";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { validatePassword } from "../lib/domain";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useDocumentTitle("Create account");

  const passwordError = password === "" ? null : validatePassword(password);
  const confirmError =
    confirm === "" || confirm === password ? null : "Passwords do not match.";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const localError = validatePassword(password);
    if (localError !== null) {
      setError(localError);
      return;
    }
    if (confirm !== password) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await register(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Registration signs you straight in. Projects, targets and findings stay scoped to your account."
      footer={
        <>
          Already registered? <Link to="/login">Sign in</Link>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        <Field label="Email">
          {({ id }) => (
            <TextInput
              id={id}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
          )}
        </Field>
        <Field label="Password" hint="8+ characters" error={passwordError}>
          {({ id, invalid }) => (
            <PasswordInput
              id={id}
              value={password}
              invalid={invalid}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              minLength={8}
              required
            />
          )}
        </Field>
        <Field label="Confirm password" error={confirmError}>
          {({ id, invalid }) => (
            <PasswordInput
              id={id}
              value={confirm}
              invalid={invalid}
              onChange={(event) => setConfirm(event.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              required
            />
          )}
        </Field>
        {error !== null && (
          <ErrorAlert title="Registration failed">{error}</ErrorAlert>
        )}
        <Button
          type="submit"
          variant="primary"
          block
          loading={submitting}
          icon={<Icon name="user" size={16} />}
        >
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthLayout>
  );
}
