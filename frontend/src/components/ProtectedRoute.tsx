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

  // In the 2.0 desktop app we always allow access and no longer
  // surface a global "offline mode" banner; individual screens
  // handle connectivity errors themselves.
  return <Outlet />;
}
