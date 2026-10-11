import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import ProjectDetail from "./pages/ProjectDetail";
import Projects from "./pages/Projects";
import Register from "./pages/Register";
import ScanResults from "./pages/ScanResults";
import TargetDetail from "./pages/TargetDetail";

function PublicOnlyRoute() {
  const { user } = useAuth();
  if (user !== null) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

/** Keeps the pre-2.0 bookmarked results URL working. */
function LegacyResultsRedirect() {
  const { targetId } = useParams();
  const [searchParams] = useSearchParams();
  const scanId = searchParams.get("scan");
  const base = `/targets/${targetId}`;
  return (
    <Navigate to={scanId !== null ? `${base}/scans/${scanId}` : base} replace />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/targets/:targetId" element={<TargetDetail />} />
          <Route
            path="/targets/:targetId/scans/:scanId"
            element={<ScanResults />}
          />
          <Route
            path="/targets/:targetId/results"
            element={<LegacyResultsRedirect />}
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
