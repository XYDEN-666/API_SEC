import { Link, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div>
      <header>
        <h1>APIShield</h1>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/projects">Projects</Link>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
