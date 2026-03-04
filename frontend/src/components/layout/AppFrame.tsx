import { NavLink } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import Button from "../ui/Button";
import { SYNC_STATE_EVENT, getSyncState, type SyncState } from "../../sync/syncState";

type Props = {
  title: string;
  children: ReactNode;
};

const navItems = [
  { to: "/builder", label: "Builder" },
  { to: "/history", label: "History" },
  { to: "/imports-exports", label: "Imports/Exports" },
  { to: "/sync-issues", label: "Sync Issues" },
  { to: "/settings", label: "Settings" },
];

export default function AppFrame({ title, children }: Props) {
  const { user, logout } = useAuth();
  const [syncState, setSyncState] = useState<SyncState>(() => getSyncState());

  useEffect(() => {
    const refresh = () => setSyncState(getSyncState());
    refresh();
    window.addEventListener(SYNC_STATE_EVENT, refresh);
    const id = window.setInterval(refresh, 2000);
    return () => {
      window.removeEventListener(SYNC_STATE_EVENT, refresh);
      window.clearInterval(id);
    };
  }, []);

  return (
    <div className="app-frame">
      <aside className="app-frame__nav">
        <p className="eyebrow">Pallet Manager 2.0</p>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `app-nav-link ${isActive ? "active" : ""}`.trim()}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <section className="app-frame__content">
        <header className="app-frame__header">
          <h1>{title}</h1>
          <div className="session-box">
            <p>
              Signed in as <strong>{user?.username}</strong>
            </p>
            <p className="sync-summary">
              Sync: {syncState.syncing ? "Syncing" : "Idle"} | Pending: {syncState.pending_count} | Review:{" "}
              {syncState.needs_review_count}
            </p>
            <Button variant="secondary" onClick={logout}>
              Log out
            </Button>
          </div>
        </header>
        {children}
      </section>
    </div>
  );
}
