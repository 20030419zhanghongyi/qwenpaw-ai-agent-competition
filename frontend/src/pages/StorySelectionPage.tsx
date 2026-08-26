import { Link } from "react-router-dom";
import { STORY_CATALOG } from "@/story-discovery/storyCatalog";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

const STORY_ORDER = [
  "lotus_city_double_map",
  "taipa_letters",
  "coloane_after_tide",
];

const COPY: Record<LanguageCode, {
  back: string; title: string; lead: string; developing: string; plannedLead: string;
  playable: (hours: number) => string; planned: string;
  regions: Record<string, string>; notes: Record<string, string>;
  stories: Record<string, { title: string; subtitle: string }>;
}> = {
  "zh-CN": {
    back: "← 返回首页", title: "选择剧情探索",
    lead: "每条故事线都是一段独立的澳门漫游。选择可游玩的故事后，将进入剧情封面页。",
    developing: "开发中", plannedLead: "后续将补充剧情、地点与谜题内容。",
    playable: (hours) => `预计 ${hours} 小时 · 点击进入`, planned: "暂不可进入 · 后续开放",
    regions: { peninsula: "澳门半岛", taipa: "氹仔", coloane: "路环" },
    notes: { lotus_city_double_map: "城市历史漫游", taipa_letters: "生活史与家书", coloane_after_tide: "路环文化漫游" },
    stories: {
      lotus_city_double_map: { title: "莲城双图：未尽之图", subtitle: "沿六处真实地点，读懂两张记录不同真实的澳门地图" },
      taipa_letters: { title: "海风寄来的信", subtitle: "沿氹仔旧城寻找五封没有收件人的信，读见岛上的家与生活" },
      coloane_after_tide: { title: "潮退之后", subtitle: "沿路环村、古庙、船厂与黑沙，补完一本没有写完的潮汐工作簿" },
    },
  },
  "zh-TW": {
    back: "← 返回首頁", title: "選擇劇情探索",
    lead: "每條故事線都是一段獨立的澳門漫遊。選擇可遊玩的故事後，將進入劇情封面頁。",
    developing: "開發中", plannedLead: "後續將補充劇情、地點及謎題內容。",
    playable: (hours) => `預計 ${hours} 小時 · 點選進入`, planned: "暫不可進入 · 後續開放",
    regions: { peninsula: "澳門半島", taipa: "氹仔", coloane: "路環" },
    notes: { lotus_city_double_map: "城市歷史漫遊", taipa_letters: "生活史與家書", coloane_after_tide: "路環文化漫遊" },
    stories: {
      lotus_city_double_map: { title: "蓮城雙圖：未盡之圖", subtitle: "沿六處真實地點，讀懂兩張記錄不同真實的澳門地圖" },
      taipa_letters: { title: "海風寄來的信", subtitle: "沿氹仔舊城尋找五封沒有收件人的信，讀見島上的家與生活" },
      coloane_after_tide: { title: "潮退之後", subtitle: "沿路環村、古廟、船廠與黑沙，補完一本沒有寫完的潮汐工作簿" },
    },
  },
  en: {
    back: "← Back to home", title: "Choose a story",
    lead: "Each story is a self-contained walk through Macau. Choose an available journey to open its story cover.",
    developing: "In development", plannedLead: "Story, places, and puzzles will be added later.",
    playable: (hours) => `About ${hours} hours · Open story`, planned: "Not yet available · Coming later",
    regions: { peninsula: "Macau Peninsula", taipa: "Taipa", coloane: "Coloane" },
    notes: { lotus_city_double_map: "Urban history walk", taipa_letters: "Everyday life and letters", coloane_after_tide: "Coloane culture walk" },
    stories: {
      lotus_city_double_map: { title: "Two Maps of the Lotus City", subtitle: "Read two different records of Macau across six real places" },
      taipa_letters: { title: "Letters Carried by the Sea Breeze", subtitle: "Follow five undelivered letters through old Taipa and discover the island's homes and everyday life" },
      coloane_after_tide: { title: "After the Tide", subtitle: "Complete an unfinished tidal workbook through Coloane village, temples, shipyards, and Hac Sa" },
    },
  },
  pt: {
    back: "← Voltar ao início", title: "Escolher uma história",
    lead: "Cada história é um passeio independente por Macau. Escolha um percurso disponível para abrir a capa.",
    developing: "Em desenvolvimento", plannedLead: "A história, os locais e os enigmas serão adicionados mais tarde.",
    playable: (hours) => `Cerca de ${hours} horas · Abrir história`, planned: "Ainda indisponível · Em breve",
    regions: { peninsula: "Península de Macau", taipa: "Taipa", coloane: "Coloane" },
    notes: { lotus_city_double_map: "Passeio pela história urbana", taipa_letters: "Vida quotidiana e cartas", coloane_after_tide: "Passeio cultural por Coloane" },
    stories: {
      lotus_city_double_map: { title: "Dois Mapas da Cidade de Lótus", subtitle: "Leia dois registos diferentes de Macau ao longo de seis lugares reais" },
      taipa_letters: { title: "Cartas trazidas pela brisa do mar", subtitle: "Siga cinco cartas sem destinatário pela Taipa antiga e descubra as casas e a vida quotidiana da ilha" },
      coloane_after_tide: { title: "Depois da Maré", subtitle: "Complete um caderno de marés inacabado pela vila, templos, estaleiros e Hac Sá" },
    },
  },
};

export function StorySelectionPage() {
  const { language } = useWalk();
  const copy = COPY[language];
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
            {copy.back}
          </Link>
          <p className="mt-6 text-[10px] font-semibold uppercase tracking-[0.24em] text-ochre">
            StoryWalk
          </p>
          <h1 className="mt-2 font-display text-3xl leading-tight text-ink">
            {copy.title}
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
            {copy.lead}
          </p>
        </header>

        <section className="grid gap-3">
          {stories.map((story, index) => {
            if (!story) return null;
            const playable = story.status === "playable";
            const localizedStory = copy.stories[story.storyId];
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
                      {copy.regions[story.region] ?? story.region}
                    </span>
                    <span className="rounded-full border border-line bg-paper-warm px-2.5 py-1 text-[10px] text-ink-soft">
                      {copy.notes[story.storyId]}
                    </span>
                    {!playable && (
                      <span className="rounded-full border border-ochre/40 bg-ochre/10 px-2.5 py-1 text-[10px] font-semibold text-ochre">
                        {copy.developing}
                      </span>
                    )}
                  </div>
                  <h2 className="mt-3 font-serif text-xl font-semibold leading-tight text-ink">
                    {localizedStory?.title ?? story.title}
                  </h2>
                  <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                    {localizedStory?.subtitle || copy.plannedLead}
                  </p>
                  <p className="mt-3 text-xs text-ink-soft">
                    {playable
                      ? copy.playable(story.estimatedHours)
                      : copy.planned}
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
