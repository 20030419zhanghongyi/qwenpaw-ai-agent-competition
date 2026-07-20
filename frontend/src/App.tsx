import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AuthPage } from "@/pages/AuthPage";
import { GuidePage } from "@/pages/GuidePage";
import { LanguagePage } from "@/pages/LanguagePage";
import { PostcardCreatePage } from "@/pages/PostcardCreatePage";
import { PostcardGalleryPage } from "@/pages/PostcardGalleryPage";
import { PostcardViewPage } from "@/pages/PostcardViewPage";
import { PreferencePage } from "@/pages/PreferencePage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RouteResultPage } from "@/pages/RouteResultPage";
import { AuthProvider } from "@/state/AuthContext";
import { TripProvider } from "@/state/TripContext";
import { WalkProvider } from "@/state/WalkContext";

export default function App() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col">
      <AuthProvider>
        <WalkProvider>
          <TripProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<LanguagePage />} />
                <Route path="/auth" element={<AuthPage />} />
                <Route element={<AppShell />}>
                  <Route path="/guide" element={<GuidePage />} />
                  <Route path="/walk" element={<RouteResultPage />} />
                  <Route path="/postcards" element={<PostcardGalleryPage />} />
                  <Route path="/postcards/new" element={<PostcardCreatePage />} />
                  <Route path="/postcards/:postcardId" element={<PostcardViewPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/preferences" element={<PreferencePage />} />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </TripProvider>
        </WalkProvider>
      </AuthProvider>
    </div>
  );
}
