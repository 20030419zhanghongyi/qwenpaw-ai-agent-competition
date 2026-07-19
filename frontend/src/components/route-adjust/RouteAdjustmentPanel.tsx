import type { LanguageCode } from "@/types";
import type { RouteAdjustmentResult } from "@/types/routes";

interface RouteAdjustmentPanelProps {
  language: LanguageCode;
  instruction: string;
  busy: boolean;
  error: string | null;
  draft: RouteAdjustmentResult | null;
  poiNames: Record<string, string>;
  onInstructionChange: (instruction: string) => void;
  onSubmit: () => void;
  onConfirm: () => void;
  onCancel: () => void;
}

const COPY: Record<
  LanguageCode,
  {
    eyebrow: string;
    title: string;
    placeholder: string;
    submit: string;
    submitting: string;
    preview: string;
    sourceAgent: string;
    sourceRules: string;
    added: string;
    removed: string;
    reordered: string;
    reasons: string;
    route: string;
    confirm: string;
    cancel: string;
  }
> = {
  "zh-CN": {
    eyebrow: "AI 路线微调",
    title: "还想怎样走？",
    placeholder: "例如：不想走太多、加一个拍照点…",
    submit: "调整路线",
    submitting: "正在调整…",
    preview: "调整预览",
    sourceAgent: "Agent 方案",
    sourceRules: "规则降级方案",
    added: "新增",
    removed: "删除",
    reordered: "重排",
    reasons: "调整原因",
    route: "调整后路线",
    confirm: "确认采用",
    cancel: "保留原路线",
  },
  "zh-TW": {
    eyebrow: "AI 路線微調",
    title: "還想怎樣走？",
    placeholder: "例如：不想走太多、加一個拍照點…",
    submit: "調整路線",
    submitting: "正在調整…",
    preview: "調整預覽",
    sourceAgent: "Agent 方案",
    sourceRules: "規則降級方案",
    added: "新增",
    removed: "刪除",
    reordered: "重排",
    reasons: "調整原因",
    route: "調整後路線",
    confirm: "確認採用",
    cancel: "保留原路線",
  },
  en: {
    eyebrow: "AI route adjustment",
    title: "How should we change it?",
    placeholder: "e.g. less walking, add a photo stop…",
    submit: "Adjust route",
    submitting: "Adjusting…",
    preview: "Adjustment preview",
    sourceAgent: "Agent proposal",
    sourceRules: "Rules fallback",
    added: "Added",
    removed: "Removed",
    reordered: "Reordered",
    reasons: "Why it changed",
    route: "Adjusted route",
    confirm: "Use this route",
    cancel: "Keep original",
  },
  pt: {
    eyebrow: "Ajuste de percurso por IA",
    title: "Como quer alterar?",
    placeholder: "ex.: caminhar menos, adicionar uma paragem para fotos…",
    submit: "Ajustar percurso",
    submitting: "A ajustar…",
    preview: "Pré-visualização",
    sourceAgent: "Proposta do Agent",
    sourceRules: "Alternativa por regras",
    added: "Adicionado",
    removed: "Removido",
    reordered: "Reordenado",
    reasons: "Motivos do ajuste",
    route: "Percurso ajustado",
    confirm: "Usar este percurso",
    cancel: "Manter o original",
  },
};

export function RouteAdjustmentPanel({
  language,
  instruction,
  busy,
  error,
  draft,
  poiNames,
  onInstructionChange,
  onSubmit,
  onConfirm,
  onCancel,
}: RouteAdjustmentPanelProps) {
  const copy = COPY[language];
  const orderedNodes = draft
    ? [...draft.route.nodes].sort((a, b) => a.order - b.order)
    : [];

  return (
    <section className="mt-6 rounded-2xl border border-sage-deep/20 bg-sage-deep/[0.04] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
        {copy.eyebrow}
      </p>
      <h3 className="mt-1 font-display text-lg text-ink">{copy.title}</h3>
      <form
        className="mt-3 flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <input
          value={instruction}
          disabled={busy}
          maxLength={4000}
          onChange={(event) => onInstructionChange(event.target.value)}
          placeholder={copy.placeholder}
          className="min-w-0 flex-1 rounded-full border border-line bg-card px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink-soft/60 focus:border-sage focus:ring-2 focus:ring-sage/30 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !instruction.trim()}
          className="shrink-0 rounded-full bg-sage-deep px-5 py-2.5 text-sm font-medium text-paper hover:bg-moss disabled:pointer-events-none disabled:opacity-50"
        >
          {busy ? copy.submitting : copy.submit}
        </button>
      </form>
      {error ? <p className="mt-3 text-xs leading-relaxed text-clay">{error}</p> : null}

      {draft ? (
        <div className="mt-5 border-t border-line/80 pt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-ink">{copy.preview}</p>
            <span className="rounded-full border border-line bg-card px-2.5 py-1 text-[10px] uppercase tracking-wider text-ink-soft">
              {draft.source === "agent" ? copy.sourceAgent : copy.sourceRules}
            </span>
          </div>

          <DiffGroup
            label={copy.added}
            tone="add"
            ids={draft.added_nodes.map((node) => node.poi_id)}
            poiNames={poiNames}
          />
          <DiffGroup
            label={copy.removed}
            tone="remove"
            ids={draft.removed_nodes.map((node) => node.poi_id)}
            poiNames={poiNames}
          />
          <DiffGroup
            label={copy.reordered}
            tone="move"
            ids={draft.reordered_nodes.map((node) => node.poi_id)}
            poiNames={poiNames}
          />

          {draft.rationale.length > 0 ? (
            <div className="mt-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-soft">
                {copy.reasons}
              </p>
              <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-ink-soft">
                {draft.rationale.map((reason) => (
                  <li key={reason}>• {reason}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-soft">
              {copy.route}
            </p>
            <ol className="mt-2 flex flex-wrap gap-1.5">
              {orderedNodes.map((node, index) => (
                <li
                  key={`${node.poi_id}-${node.order}`}
                  className="rounded-full border border-line bg-card px-3 py-1.5 text-[11px] text-ink"
                >
                  {index + 1}. {poiNames[node.poi_id] ?? node.poi_id}
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-full border border-line bg-card px-4 py-2.5 text-sm text-ink hover:bg-paper-warm"
            >
              {copy.cancel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="rounded-full bg-sage-deep px-4 py-2.5 text-sm font-medium text-paper hover:bg-moss"
            >
              {copy.confirm}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function DiffGroup({
  label,
  tone,
  ids,
  poiNames,
}: {
  label: string;
  tone: "add" | "remove" | "move";
  ids: string[];
  poiNames: Record<string, string>;
}) {
  const uniqueIds = [...new Set(ids)];
  if (uniqueIds.length === 0) return null;
  const toneClass = {
    add: "border-sage/35 bg-sage-deep/10 text-sage-deep",
    remove: "border-clay/35 bg-clay/10 text-clay",
    move: "border-ochre/35 bg-ochre/10 text-ink",
  }[tone];

  return (
    <div className="mt-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-soft">
        {label}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {uniqueIds.map((poiId) => (
          <span key={poiId} className={`rounded-full border px-2.5 py-1 text-[11px] ${toneClass}`}>
            {poiNames[poiId] ?? poiId}
          </span>
        ))}
      </div>
    </div>
  );
}
