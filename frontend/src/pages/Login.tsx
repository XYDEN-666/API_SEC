import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AuthLayout from "../components/AuthLayout";
import Icon from "../components/Icon";
import Button from "../components/ui/Button";
import { ErrorAlert, InfoAlert } from "../components/ui/Feedback";
import { Field, PasswordInput, TextInput } from "../components/ui/Field";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export default function Login() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useDocumentTitle("Sign in");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Use the account that owns the projects you want to assess."
      footer={
        <>
          No account yet? <Link to="/register">Create one</Link>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {sessionExpired && (
          <InfoAlert tone="warning" title="Session ended">
            Your session expired or was rejected. Sign in again to continue.
          </InfoAlert>
        )}
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
        <Field label="Password">
          {({ id }) => (
            <PasswordInput
              id={id}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          )}
        </Field>
        {error !== null && (
          <ErrorAlert title="Sign in failed">{error}</ErrorAlert>
        )}
        <Button
          type="submit"
          variant="primary"
          block
          loading={submitting}
          icon={<Icon name="logout" size={16} />}
        >
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
}
