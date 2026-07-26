/**
 * InvitationDecision — fullscreen cinematic accept / decline prompt.
 *
 * v2: This component is a standalone reusable decision screen for future
 *     story packages that may not use the full cutscene pipeline.
 *     The main cutscene flow now uses the DecisionScene inside CutsceneStage,
 *     which provides the same visual language integrated into the cutscene.
 *
 * Visual direction: historical archive × mysterious letter.
 * The screen is fully opaque — no PreferencePage visible behind it.
 *
 * This component is PURE UI — it does NOT:
 *  - call any Story API
 *  - read/write localStorage
 *  - navigate
 *  - inspect auth state
 */

export interface InvitationDecisionProps {
  /** Preamble text shown before the question. */
  preamble: string;
  /** The question to ask the user. */
  question: string;
  /** Primary CTA label. */
  acceptLabel: string;
  /** Secondary label. */
  declineLabel: string;
  /** Fired when user clicks Accept. */
  onAccept: () => void;
  /** Fired when user clicks Decline. */
  onDecline: () => void;
  /** Disables both buttons (e.g., during transition). */
  loading?: boolean;
}

export function InvitationDecision({
  preamble,
  question,
  acceptLabel,
  declineLabel,
  onAccept,
  onDecline,
  loading = false,
}: InvitationDecisionProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0e0d0c] px-6"
      style={{ paddingBottom: "max(3rem, env(safe-area-inset-bottom, 0px))" }}
    >
      {/* Warm radial glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 40%, rgba(200,170,120,0.04) 0%, transparent 65%)",
        }}
        aria-hidden
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center">
        {/* Preamble */}
        <p className="font-serif text-lg leading-loose tracking-[0.04em] text-paper/70 sm:text-xl">
          {preamble}
        </p>

        {/* Question */}
        <p className="mt-8 font-serif text-xl leading-loose tracking-[0.04em] text-paper/90 sm:text-2xl">
          {question}
        </p>

        {/* Buttons */}
        <div className="mt-12 w-full max-w-[420px] space-y-3">
          {/* Accept — warm muted gold, not bright yellow */}
          <button
            type="button"
            disabled={loading}
            onClick={onAccept}
            className="w-full rounded-full border border-ochre/40 bg-ochre/15 px-6 py-4 text-base font-medium tracking-[0.04em] text-ochre transition hover:border-ochre/60 hover:bg-ochre/20 active:scale-[0.99] disabled:opacity-30"
          >
            {acceptLabel}
          </button>

          {/* Decline — text/outline only */}
          <button
            type="button"
            disabled={loading}
            onClick={onDecline}
            className="w-full rounded-full border border-paper/10 px-6 py-4 text-base font-medium tracking-[0.04em] text-paper/30 transition hover:border-paper/25 hover:text-paper/50 active:scale-[0.99] disabled:opacity-20"
          >
            {declineLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
