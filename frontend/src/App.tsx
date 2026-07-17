import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { GuidePage } from "@/pages/GuidePage";
import { LanguagePage } from "@/pages/LanguagePage";
import { PreferencePage } from "@/pages/PreferencePage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RouteResultPage } from "@/pages/RouteResultPage";
import { WalkProvider } from "@/state/WalkContext";

export default function App() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col">
      <WalkProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LanguagePage />} />
            <Route element={<AppShell />}>
              <Route path="/guide" element={<GuidePage />} />
              <Route path="/walk" element={<RouteResultPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/preferences" element={<PreferencePage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </WalkProvider>
    </div>
  );
}
