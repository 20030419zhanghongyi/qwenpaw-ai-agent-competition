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
import { StoryCoverPage } from "@/pages/StoryCoverPage";
import { StorySelectionPage } from "@/pages/StorySelectionPage";
import { StoryMapPage } from "@/pages/StoryMapPage";
import { StoryScenePage } from "@/pages/StoryScenePage";
import { StoryEndingPage } from "@/pages/StoryEndingPage";
import { AuthProvider } from "@/state/AuthContext";
import { StoryProvider } from "@/state/StoryContext";
import { TripProvider } from "@/state/TripContext";
import { WalkProvider } from "@/state/WalkContext";

export default function App() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col">
      <AuthProvider>
        <WalkProvider>
          <TripProvider>
            <StoryProvider>
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
                  {/* StoryWalk — independent product mode */}
                  <Route path="/stories" element={<StorySelectionPage />} />
                  <Route path="/stories/:storyId" element={<StoryCoverPage />} />
                  <Route path="/story-sessions/:sessionId/map" element={<StoryMapPage />} />
                  <Route path="/story-sessions/:sessionId/nodes/:nodeId" element={<StoryScenePage />} />
                  <Route path="/story-sessions/:sessionId/ending" element={<StoryEndingPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </BrowserRouter>
            </StoryProvider>
          </TripProvider>
        </WalkProvider>
      </AuthProvider>
    </div>
  );
}
