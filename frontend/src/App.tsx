import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import HistoryExplorerPage from "./pages/HistoryExplorerPage";
import LiveBuilderPage from "./pages/LiveBuilderPage";
import ImportExportPage from "./pages/ImportExportPage";
import SettingsPage from "./pages/SettingsPage";
import SyncIssuesPage from "./pages/SyncIssuesPage";
import CustomersPage from "./pages/CustomersPage";
import ExportsPage from "./pages/ExportsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/builder" replace />} />
        <Route path="/builder" element={<LiveBuilderPage />} />
        <Route path="/history" element={<HistoryExplorerPage />} />
        <Route path="/imports-exports" element={<ImportExportPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/exports" element={<ExportsPage />} />
        <Route path="/sync-issues" element={<SyncIssuesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
