import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LoadingState, ErrorState } from "@/components/common/States";
import { useAuth } from "@/state/AuthContext";
import { useStory, useStoryRestore } from "@/state/StoryContext";
import type { StoryAction, StoryEndingOption } from "@/types/stories";

export function StoryEndingPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const {
    session,
    story,
    loading,
    error,
    restoreSession,
    submitAction,
  } = useStory();
  const { sessionId: persistedId } = useStoryRestore();

  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [reflection, setReflection] = useState("");
  const [selectedEnding, setSelectedEnding] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const effectiveId = sessionId ?? persistedId;
  useEffect(() => {
    if (effectiveId && token) {
      restoreSession(effectiveId);
    }
  }, [effectiveId, token, restoreSession]);

  const isCompleted = session?.status === "completed";
  const savedEndingId = session?.state.ending_id;
  const savedReflection = session?.state.ending_reflection;
  const currentChapter = session?.current_chapter;

  // Get available endings
  const endings: StoryEndingOption[] =
    currentChapter?.ending_options ??
    (currentChapter?.kind === "ending" ? story?.endings.map((e) => ({ ...e, text: undefined })) : []) ??
    [];

  const savedEnding = isCompleted && savedEndingId
    ? endings.find((e) => e.id === savedEndingId)
    : null;
  const endingImageSrc =
    story?.id === "coloane_after_tide"
      ? "/story/coloane-after-tide/sound-postcard.jpg"
      : null;

  const handleSubmit = async (action: StoryAction) => {
    if (!currentChapter || !session) return;
    setBusy(true);
    setLocalError(null);
    try {
      if (action === "choose_ending") {
        if (!selectedEnding) {
          setLocalError("请选择一个结局");
          setBusy(false);
          return;
        }
        await submitAction({
          action,
          chapter_id: currentChapter.id,
          choice_id: selectedEnding,
          reflection: reflection || undefined,
        });
        setSubmitted(true);
      }
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  if (loading && !session) return <LoadingState label="加载结局…" />;
  if (error && !session) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState
          message={error}
          onRetry={() => effectiveId && restoreSession(effectiveId)}
        />
      </div>
    );
  }
  if (!session) {
    return (
      <div className="flex min-h-dvh flex-col bg-paper px-4 py-8">
        <ErrorState message="未找到故事会话" />
      </div>
    );
  }

  return (
    <main className="flex min-h-dvh flex-col bg-paper text-ink">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/95 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() =>
              navigate(`/story-sessions/${effectiveId}/map`)
            }
            className="text-sm text-ink-soft transition hover:text-ink"
          >
            ← 故事地图
          </button>
          <p className="font-serif text-sm font-semibold text-ink">终章</p>
          <div className="w-12" aria-hidden />
        </div>
      </header>

      <div className="flex-1 overflow-auto px-4 py-6 sm:mx-auto sm:max-w-lg sm:px-6">
        {endingImageSrc && (
          <img
            src={endingImageSrc}
            alt=""
            className="mb-6 h-56 w-full rounded-2xl border border-line object-cover"
            loading="lazy"
          />
        )}

        {/* Timeline Reconstruction scene */}
        {currentChapter?.scene && (
          <div className="mb-6 rounded-2xl border border-line bg-card p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
              时间重建
            </p>
            <p className="mt-2 text-sm leading-relaxed text-ink">
              {currentChapter.scene}
            </p>
          </div>
        )}

        {/* Knowledge cards for ending */}
        {currentChapter?.knowledge_cards && currentChapter.knowledge_cards.length > 0 && (
          <div className="mb-6 space-y-2">
            {currentChapter.knowledge_cards.map((card, i) => (
              <div
                key={i}
                className="rounded-xl border border-line bg-paper-warm p-4"
              >
                <p className="text-xs font-semibold text-sage-deep">
                  {card.title}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                  {card.text}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Collected rewards */}
        {session.state.rewards.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
              已收集的线索
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {session.state.rewards.map((r) => {
                const icons: Record<string, string> = {
                  stamp: "🦭",
                  capability: "🔍",
                  coordinate: "📍",
                };
                return (
                  <span
                    key={r.id}
                    className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-3 py-1.5 text-xs"
                  >
                    <span>{icons[r.kind] ?? "✦"}</span>
                    <span className="text-ink-soft">{r.name ?? r.id}</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Already completed */}
        {isCompleted && savedEnding ? (
          <div className="mb-6 rounded-2xl border border-sage-deep/40 bg-sage-deep/5 p-6 text-center">
            <p className="text-3xl" aria-hidden>
              📜
            </p>
            <p className="mt-3 font-serif text-xl font-semibold text-sage-deep">
              {savedEnding.title}
            </p>
            <p className="mt-2 text-sm text-ink-soft">
              {savedEnding.text ?? ""}
            </p>
            {savedReflection && (
              <div className="mt-4 rounded-xl border border-line bg-paper p-4">
                <p className="text-xs font-semibold text-ink-soft">你的反思</p>
                <p className="mt-1 text-sm italic text-ink">
                  "{savedReflection}"
                </p>
              </div>
            )}
            <button
              type="button"
              onClick={() => navigate("/postcards/new")}
              className="mt-5 rounded-full bg-sage-deep px-6 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              生成我的澳门时间明信片 →
            </button>
          </div>
        ) : submitted ? (
          /* Just submitted */
          <div className="mb-6 rounded-2xl border border-sage-deep/40 bg-sage-deep/5 p-6 text-center">
            <p className="text-3xl" aria-hidden>
              ✨
            </p>
            <p className="mt-3 font-serif text-xl font-semibold text-sage-deep">
              故事完成
            </p>
            <p className="mt-2 text-sm text-ink-soft">
              你的选择已被保存
            </p>
            <button
              type="button"
              onClick={() => navigate("/postcards/new")}
              className="mt-5 rounded-full bg-sage-deep px-6 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
            >
              生成我的澳门时间明信片 →
            </button>
          </div>
        ) : (
          /* Choose ending */
          <>
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
                你的选择
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                你将如何完成{story?.title ? `《${story.title}》` : "这段旅程"}的最后一页？
              </p>
            </div>

            {localError && (
              <div className="mb-4 rounded-xl border border-clay/30 bg-clay/5 p-3 text-sm text-clay">
                {localError}
              </div>
            )}

            <div className="space-y-3 mb-6">
              {endings.map((ending) => (
                <button
                  key={ending.id}
                  type="button"
                  disabled={busy}
                  onClick={() => setSelectedEnding(ending.id)}
                  className={`w-full rounded-xl border px-4 py-4 text-left transition ${
                    selectedEnding === ending.id
                      ? "border-sage-deep bg-sage-deep/10"
                      : "border-line bg-card hover:border-sage"
                  } disabled:opacity-50`}
                >
                  <p className="font-serif text-base font-semibold text-ink">
                    {ending.title}
                  </p>
                  <p className="mt-1 text-sm text-ink-soft">
                    {ending.choice_text}
                  </p>
                </button>
              ))}
            </div>

            {/* Optional reflection */}
            <div className="mb-6">
              <label className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">
                你的反思（可选）
              </label>
              <textarea
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                maxLength={2000}
                rows={3}
                placeholder="旅程结束后，你有什么想记下的？"
                className="mt-2 w-full resize-none rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink placeholder:text-ink-soft/60 focus:border-sage-deep focus:outline-none"
              />
            </div>

            <button
              type="button"
              disabled={busy || !selectedEnding}
              onClick={() => handleSubmit("choose_ending")}
              className="w-full rounded-full bg-ochre px-6 py-4 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition hover:opacity-90 active:scale-[0.99] disabled:opacity-40"
            >
              {busy ? "保存中…" : "确认选择"}
            </button>
          </>
        )}
      </div>
    </main>
  );
}
