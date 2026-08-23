import { Link } from "react-router-dom";
import { STORY_CATALOG } from "@/story-discovery/storyCatalog";

const STORY_ORDER = [
  "lotus_city_double_map",
  "taipa_letters",
  "coloane_after_tide",
];

const REGION_LABELS: Record<string, string> = {
  peninsula: "澳门半岛",
  taipa: "氹仔",
  coloane: "路环",
};

const STORY_NOTES: Record<string, string> = {
  lotus_city_double_map: "原有故事模式一",
  taipa_letters: "生活史与家书",
  coloane_after_tide: "路環文化漫遊",
};

export function StorySelectionPage() {
  const stories = STORY_ORDER.map((storyId) =>
    STORY_CATALOG.find((entry) => entry.storyId === storyId),
  ).filter(Boolean);

  return (
    <main className="min-h-dvh bg-paper px-4 py-6 text-ink sm:px-6">
      <div className="mx-auto flex min-h-[calc(100dvh-3rem)] max-w-3xl flex-col">
        <header className="mb-6">
          <Link
            to="/"
            className="text-sm text-ink-soft transition hover:text-ink"
          >
            ← 返回首页
          </Link>
          <p className="mt-6 text-[10px] font-semibold uppercase tracking-[0.24em] text-ochre">
            StoryWalk
          </p>
          <h1 className="mt-2 font-display text-3xl leading-tight text-ink">
            选择剧情探索
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
            每条故事线是一段独立的澳门漫游。选择一个可游玩的故事后，会进入剧情封面页。
          </p>
        </header>

        <section className="grid gap-3">
          {stories.map((story, index) => {
            if (!story) return null;
            const playable = story.status === "playable";
            const cardClass =
              "group flex w-full items-stretch gap-4 rounded-2xl border p-4 text-left shadow-[var(--shadow-soft)] transition";
            const content = (
              <>
                <div
                  className={`grid size-12 shrink-0 place-items-center rounded-xl font-serif text-lg font-bold ${
                    playable
                      ? "bg-sage-deep text-paper"
                      : "bg-paper-warm text-ink-soft"
                  }`}
                  aria-hidden
                >
                  {index + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-line bg-paper-warm px-2.5 py-1 text-[10px] font-semibold text-sage-deep">
                      {REGION_LABELS[story.region] ?? story.region}
                    </span>
                    <span className="rounded-full border border-line bg-paper-warm px-2.5 py-1 text-[10px] text-ink-soft">
                      {STORY_NOTES[story.storyId]}
                    </span>
                    {!playable && (
                      <span className="rounded-full border border-ochre/40 bg-ochre/10 px-2.5 py-1 text-[10px] font-semibold text-ochre">
                        开发中
                      </span>
                    )}
                  </div>
                  <h2 className="mt-3 font-serif text-xl font-semibold leading-tight text-ink">
                    {story.title}
                  </h2>
                  <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                    {story.subtitle || "后续将补充剧情、地点与谜题内容。"}
                  </p>
                  <p className="mt-3 text-xs text-ink-soft">
                    {playable
                      ? `预计 ${story.estimatedHours} 小时 · 点击进入`
                      : "暂不可进入 · 作为后续故事位保留"}
                  </p>
                </div>
                <span
                  className={`self-center text-xl ${
                    playable ? "text-sage-deep" : "text-ink-soft/40"
                  }`}
                  aria-hidden
                >
                  →
                </span>
              </>
            );

            return playable ? (
              <Link
                key={story.storyId}
                to={`/stories/${story.storyId}`}
                className={`${cardClass} border-line bg-card hover:border-sage hover:bg-paper-warm active:scale-[0.99]`}
              >
                {content}
              </Link>
            ) : (
              <div
                key={story.storyId}
                className={`${cardClass} cursor-not-allowed border-line bg-card/60 opacity-70`}
                aria-disabled="true"
              >
                {content}
              </div>
            );
          })}
        </section>

        <div className="calcada-wave mt-auto h-2.5 shrink-0 opacity-50" />
      </div>
    </main>
  );
}
