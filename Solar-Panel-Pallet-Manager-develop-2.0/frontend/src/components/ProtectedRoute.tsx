import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute() {
  const { canAccessApp, isInitializing, isOfflineSession } = useAuth();

  if (isInitializing) {
    return <main className="auth-loading">Loading session...</main>;
  }

  if (!canAccessApp) {
    return (
      <main className="auth-loading">
        <p>Unable to initialize session. Configure backend settings and retry.</p>
        <Link className="inline-link" to="/settings">
          Open Settings
        </Link>
      </main>
    );
  }

  return (
    <>
      {isOfflineSession ? (
        <div className="status-banner status-banner--warning">
          Offline mode: changes will sync when the server is reachable.
        </div>
      ) : null}
      <Outlet />
    </>
  );
}
