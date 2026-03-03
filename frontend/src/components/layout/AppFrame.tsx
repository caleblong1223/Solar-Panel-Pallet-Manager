import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import Button from "../ui/Button";

type Props = {
  title: string;
  children: ReactNode;
};

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/builder", label: "Builder" },
  { to: "/history", label: "History" },
  { to: "/imports-exports", label: "Imports/Exports" },
];

export default function AppFrame({ title, children }: Props) {
  const { user, logout } = useAuth();

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
