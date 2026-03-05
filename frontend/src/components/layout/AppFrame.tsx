import { NavLink } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import { SYNC_STATE_EVENT, getSyncState, type SyncState } from "../../sync/syncState";

type Props = {
  title: string;
  children: ReactNode;
};

const navItems = [
  { to: "/builder", label: "Builder" },
  { to: "/history", label: "History" },
  { to: "/imports-exports", label: "Import" },
  { to: "/customers", label: "Customer Management" },
  { to: "/settings", label: "Settings" },
];

export default function AppFrame({ title, children }: Props) {
  const { isOfflineSession } = useAuth();
  const [syncState, setSyncState] = useState<SyncState>(() => getSyncState());

  useEffect(() => {
    const refresh = () => setSyncState(getSyncState());
    refresh();
    window.addEventListener(SYNC_STATE_EVENT, refresh);
    return () => {
      window.removeEventListener(SYNC_STATE_EVENT, refresh);
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
              Connection: <strong>{isOfflineSession ? "Offline (cached)" : "Online"}</strong>
            </p>
            <p className="sync-summary">
              Sync: {syncState.syncing ? "Syncing" : "Idle"} | Pending: {syncState.pending_count} | Review:{" "}
              {syncState.needs_review_count}
            </p>
          </div>
        </header>
        {children}
      </section>
    </div>
  );
}
