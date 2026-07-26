/**
 * StoryInvitationDevPreview — TEMPORARY harness for visual validation.
 *
 * REMOVE this file in Step 4 (PreferencePage integration).
 *
 * Usage (temporary — drop into any page for testing):
 *   import { StoryInvitationDevPreview } from "@/components/story-invitation/StoryInvitationDevPreview";
 *   // then render <StoryInvitationDevPreview />
 *
 * This component is self-contained: a button to launch the cutscene,
 * then the full StoryInvitationExperience with no-op callbacks.
 */

import { useCallback, useState } from "react";
import { StoryInvitationExperience } from "./StoryInvitationExperience";
import { LOTUS_TELEGRAM_SCENES } from "./scenes/lotusTelegram";

export function StoryInvitationDevPreview() {
  const [show, setShow] = useState(false);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const handleAccept = useCallback(() => {
    setShow(false);
    setLastAction("accepted");
  }, []);

  const handleDecline = useCallback(() => {
    setShow(false);
    setLastAction("declined");
  }, []);

  return (
    <>
      {/* Launch button */}
      <div className="flex flex-col items-center gap-3 p-8">
        <button
          type="button"
          onClick={() => {
            setLastAction(null);
            setShow(true);
          }}
          className="rounded-full bg-sage-deep px-6 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
        >
          Preview: Lotus Telegram Cutscene
        </button>
        {lastAction && (
          <p className="text-xs text-ink-soft">
            Last action: <span className="font-semibold text-sage-deep">{lastAction}</span>
          </p>
        )}
      </div>

      {/* Cutscene experience */}
      {show && (
        <StoryInvitationExperience
          scenes={LOTUS_TELEGRAM_SCENES}
          onAccept={handleAccept}
          onDecline={handleDecline}
        />
      )}
    </>
  );
}
