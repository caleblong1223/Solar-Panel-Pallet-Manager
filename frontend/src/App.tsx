import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppHomePage from "./pages/AppHomePage";
import HistoryExplorerPage from "./pages/HistoryExplorerPage";
import LiveBuilderPage from "./pages/LiveBuilderPage";
import ImportExportPage from "./pages/ImportExportPage";
import SettingsPage from "./pages/SettingsPage";
import SyncIssuesPage from "./pages/SyncIssuesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<AppHomePage />} />
        <Route path="/builder" element={<LiveBuilderPage />} />
        <Route path="/history" element={<HistoryExplorerPage />} />
        <Route path="/imports-exports" element={<ImportExportPage />} />
        <Route path="/sync-issues" element={<SyncIssuesPage />} />
      </Route>
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
