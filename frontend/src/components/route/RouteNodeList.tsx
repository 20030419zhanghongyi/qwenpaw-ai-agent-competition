export interface DisplayNode {
  poiId: string;
  order: number;
  name: string;
  subtitle?: string;
  note: string;
  stayMin: number;
  state: "current" | "next" | "upcoming";
}

export function RouteNodeList({
  nodes,
  stayLabel = "min",
  onSelectIndex,
}: {
  nodes: DisplayNode[];
  stayLabel?: string;
  onSelectIndex?: (index: number) => void;
}) {
  return (
    <ol className="relative space-y-6">
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

        return (
          <li key={p.poiId} className="relative flex gap-4">
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
          </li>
        );
      })}
    </ol>
  );
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
