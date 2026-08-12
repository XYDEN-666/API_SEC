import { useAuth } from "../auth/AuthContext";

export default function Home() {
  const { user, logout } = useAuth();

  return (
    <section>
      <h2>Dashboard</h2>
      {user !== null && (
        <p>
          Signed in as {user.email} ({user.role})
        </p>
      )}
      <button type="button" onClick={logout}>
        Log out
      </button>
    </section>
  );
}
