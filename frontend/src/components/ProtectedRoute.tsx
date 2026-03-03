import { Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth();

  if (isInitializing) {
    return <main className="auth-loading">Loading session...</main>;
  }

  if (!isAuthenticated) {
    return (
      <main className="auth-loading">
        Unable to initialize session. Please check connection to the server.
      </main>
    );
  }

  return <Outlet />;
}
