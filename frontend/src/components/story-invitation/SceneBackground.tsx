/**
 * SceneBackground — per-scene CSS background layers.
 *
 * Each background uses a near-black base (#0e0d0c, a very slightly warm black)
 * with decorative layers that suggest old documents, maps, and letters.
 *
 * ALL layers have pointer-events-none so clicks reach interactive content.
 */

import type { CutsceneScene } from "./scenes/lotusTelegram";

export function SceneBackground({
  background,
}: {
  background: CutsceneScene["background"];
}) {
  switch (background) {
    // ── Dark: warm-black, minimal — "archive room" ────────────────────
    case "dark":
      return (
        <div className="pointer-events-none absolute inset-0 bg-[#0e0d0c]">
          {/* Faint warm radial glow from centre */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse at 50% 40%, rgba(180,150,110,0.04) 0%, transparent 70%)",
            }}
            aria-hidden
          />
        </div>
      );

    // ── Maps: two translucent parchment-like panels ───────────────────
    case "maps":
      return (
        <div className="pointer-events-none absolute inset-0 overflow-hidden bg-[#0e0d0c]">
          {/* Warm glow */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse at 50% 45%, rgba(200,170,120,0.05) 0%, transparent 65%)",
            }}
            aria-hidden
          />
          {/* Panel 1 — warm ochre parchment, counter-clockwise */}
          <div
            className="pointer-events-none absolute inset-[14%] rounded-sm border border-ochre/12"
            style={{
              backgroundImage: `
                linear-gradient(rgba(200,170,130,0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(200,170,130,0.04) 1px, transparent 1px)
              `,
              backgroundSize: "56px 56px",
              transform: "rotate(-2.2deg)",
              boxShadow: "0 0 80px rgba(180,150,100,0.03)",
            }}
          />
          {/* Panel 2 — muted sage, clockwise + offset */}
          <div
            className="pointer-events-none absolute inset-[12%] rounded-sm border border-sage/6"
            style={{
              backgroundImage: `
                linear-gradient(rgba(150,175,155,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(150,175,155,0.035) 1px, transparent 1px)
              `,
              backgroundSize: "56px 56px",
              transform: "rotate(1.5deg) translate(10px, -8px)",
              boxShadow: "0 0 60px rgba(140,170,140,0.025)",
            }}
          />
        </div>
      );

    // ── Telegram / Letter: warm archival border ───────────────────────
    case "telegram":
      return (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[#0e0d0c]">
          {/* Warm radial glow */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse at 50% 50%, rgba(200,170,120,0.06) 0%, transparent 60%)",
            }}
            aria-hidden
          />
          {/* Letter border — warm ochre, like aged paper */}
          <div className="pointer-events-none absolute inset-[6%] rounded-sm border border-ochre/12 bg-ochre/[0.015]" />
        </div>
      );

    default:
      return (
        <div className="pointer-events-none absolute inset-0 bg-[#0e0d0c]" />
      );
  }
}
