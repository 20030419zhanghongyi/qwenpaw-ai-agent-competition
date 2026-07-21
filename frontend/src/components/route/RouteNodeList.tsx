export interface DisplayNode {
  poiId: string;
  order: number;
  name: string;
  subtitle?: string;
  note: string;
  stayMin: number;
  state: "current" | "next" | "upcoming";
}

export interface WalkLeg {
  walkM: number;
  walkMin: number;
  busLines?: string[];
  busFromStop?: string | null;
  busToStop?: string | null;
  /** When walk > ~15 min and bus exists, UI leads with bus. */
  preferredMode?: "walk" | "bus" | string;
}

export function RouteNodeList({
  nodes,
  legs = [],
  legsLoading = false,
  stayLabel = "min",
  walkLegLabel = "步行约 {min} 分钟 · {dist}",
  busLegLabel = "巴士 {lines}",
  busStopLegLabel = "{from} → {to}",
  legsLoadingLabel = "正在查询步行与巴士…",
  onSelectIndex,
}: {
  nodes: DisplayNode[];
  /** Legs[i] connects nodes[i] → nodes[i + 1]. */
  legs?: WalkLeg[];
  legsLoading?: boolean;
  stayLabel?: string;
  walkLegLabel?: string;
  busLegLabel?: string;
  busStopLegLabel?: string;
  legsLoadingLabel?: string;
  onSelectIndex?: (index: number) => void;
}) {
  return (
    <ol className="relative space-y-0">
      {legsLoading ? (
        <p className="mb-3 pl-12 text-[11px] tracking-wide text-ink-soft">{legsLoadingLabel}</p>
      ) : null}
      <span className="absolute bottom-2 left-[15px] top-2 w-px bg-line" aria-hidden />
      {nodes.map((p, index) => {
        const selectable = Boolean(onSelectIndex);
        const markerClass = [
          "relative z-10 grid size-8 shrink-0 place-items-center rounded-full font-serif text-xs font-bold transition",
          p.state === "current"
            ? "bg-sage-deep text-paper"
            : p.state === "next"
              ? "bg-paper text-sage-deep ring-2 ring-sage-deep"
              : "bg-paper text-ink-soft ring-1 ring-line",
          selectable
            ? "cursor-pointer hover:scale-105 hover:ring-2 hover:ring-sage focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
            : "",
        ].join(" ");
        const leg = legs[index];
        const busLines = (leg?.busLines ?? []).filter(Boolean);
        const busFromStop = leg?.busFromStop?.trim() || "";
        const busToStop = leg?.busToStop?.trim() || "";
        const hasBusStops = Boolean(busFromStop && busToStop);

        return (
          <li key={p.poiId} className="relative">
            <div className="flex gap-4">
              {selectable ? (
                <button
                  type="button"
                  aria-current={p.state === "current" ? "step" : undefined}
                  aria-label={p.name}
                  onClick={() => onSelectIndex?.(index)}
                  className={markerClass}
                >
                  {p.order}
                </button>
              ) : (
                <div className={markerClass}>{p.order}</div>
              )}
              <div className="min-w-0 flex-1 pb-1">
                {selectable ? (
                  <button
                    type="button"
                    onClick={() => onSelectIndex?.(index)}
                    className="w-full rounded-lg text-left transition hover:bg-paper-warm/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage/40"
                  >
                    <NodeCopy node={p} stayLabel={stayLabel} />
                  </button>
                ) : (
                  <NodeCopy node={p} stayLabel={stayLabel} />
                )}
              </div>
            </div>
            {leg && index < nodes.length - 1 ? (
              <div className="relative ml-[15px] flex flex-wrap items-center gap-1.5 py-3 pl-8">
                <span
                  className="absolute left-0 top-0 h-full w-px bg-sage/40"
                  aria-hidden
                />
                {leg.preferredMode === "bus" && busLines.length > 0 ? (
                  <>
                    <span className="max-w-full rounded-full border border-ochre/40 bg-ochre/15 px-3 py-1 text-[11px] font-medium leading-snug tracking-wide text-ink">
                      {formatBusLeg(busLegLabel, busStopLegLabel, busLines, {
                        from: busFromStop,
                        to: busToStop,
                        hasStops: hasBusStops,
                      })}
                    </span>
                    <span className="rounded-full border border-line/80 bg-paper px-3 py-1 text-[11px] tracking-wide text-ink-soft">
                      {formatWalkLeg(walkLegLabel, leg)}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="rounded-full border border-sage/30 bg-sage-deep/[0.06] px-3 py-1 text-[11px] tracking-wide text-sage-deep">
                      {formatWalkLeg(walkLegLabel, leg)}
                    </span>
                    {busLines.length > 0 ? (
                      <span className="max-w-full rounded-full border border-ochre/35 bg-ochre/10 px-3 py-1 text-[11px] leading-snug tracking-wide text-ink">
                        {formatBusLeg(busLegLabel, busStopLegLabel, busLines, {
                          from: busFromStop,
                          to: busToStop,
                          hasStops: hasBusStops,
                        })}
                      </span>
                    ) : null}
                  </>
                )}
              </div>
            ) : index < nodes.length - 1 ? (
              <div className="h-6" aria-hidden />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

function formatWalkLeg(template: string, leg: WalkLeg): string {
  const dist =
    leg.walkM >= 1000
      ? `${(leg.walkM / 1000).toFixed(leg.walkM >= 10000 ? 0 : 1)} km`
      : `${leg.walkM} m`;
  return template.replace("{min}", String(leg.walkMin)).replace("{dist}", dist);
}

function formatBusLeg(
  linesTemplate: string,
  stopsTemplate: string,
  lines: string[],
  stops: { from: string; to: string; hasStops: boolean },
): string {
  // Prefer concrete AMap transfer chains (already use " → "); show up to 2 plan options.
  const linesText = linesTemplate.replace("{lines}", lines.slice(0, 2).join(" · "));
  if (!stops.hasStops) return linesText;
  const stopsText = stopsTemplate
    .replace("{from}", stops.from)
    .replace("{to}", stops.to);
  return `${linesText} · ${stopsText}`;
}

function NodeCopy({ node, stayLabel }: { node: DisplayNode; stayLabel: string }) {
  return (
    <>
      <div className="flex items-baseline justify-between gap-2">
        <p className="truncate font-display text-base text-ink">{node.name}</p>
        <span className="shrink-0 text-[10px] uppercase tracking-widest text-ink-soft">
          {node.stayMin} {stayLabel}
        </span>
      </div>
      {node.subtitle ? (
        <p className="text-[11px] uppercase tracking-widest text-ink-soft">{node.subtitle}</p>
      ) : null}
      <p className="mt-1 text-xs leading-relaxed text-ink-soft">{node.note}</p>
    </>
  );
}
