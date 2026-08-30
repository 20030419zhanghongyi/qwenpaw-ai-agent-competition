import type { LanguageCode } from "@/types";
import type { StorySelection } from "@/types";
import { StoryImage } from "../assets";
import type { StoryId } from "../storyMetadata";

export type { StoryId } from "../storyMetadata";

const STORIES: Array<{
  id: StoryId;
  assetId: string;
  hours: number;
  region: "peninsula" | "taipa" | "coloane";
}> = [
  { id: "lotus_city_double_map", assetId: "V4-ENTRY-01", hours: 7, region: "peninsula" },
  { id: "taipa_letters", assetId: "TAI-COVER-01", hours: 4, region: "taipa" },
  { id: "coloane_after_tide", assetId: "CAT-COVER-01", hours: 4, region: "coloane" },
];

const COPY = {
  "zh-CN": {
    eyebrow: "故事体验 · 可选",
    title: "选择一条澳门故事线",
    lead: "选择后，我们会把这条故事线安排进你的正常路线；不参加也不会影响基础行程服务。",
    open: "选择这条故事线",
    decline: "这次不参加故事",
    required: "多日行程需要选择故事安排在第几天。",
    limit: "每一天最多安排一条故事；如需选择更多故事，请增加行程天数。",
    chooseDay: "请选择日期",
    dayLabel: "安排故事日期",
    dayOption: (day: number, date: string) => `第 ${day} 天 · ${date}`,
    hours: (hours: number) => `约 ${hours} 小时`,
    regions: { peninsula: "澳门半岛", taipa: "氹仔", coloane: "路环" },
    stories: {
      lotus_city_double_map: { title: "莲城双图：未尽之图", subtitle: "沿六处真实地点，读懂两张记录不同真实的澳门地图" },
      taipa_letters: { title: "海风寄来的信", subtitle: "沿氹仔旧城寻找五封没有收件人的信，读见岛上的家与生活" },
      coloane_after_tide: { title: "潮退之后", subtitle: "沿路环村、古庙、船厂与黑沙，补完一本没有写完的潮汐工作簿" },
    },
  },
  "zh-TW": {
    eyebrow: "故事體驗 · 可選",
    title: "選擇一條澳門故事線",
    lead: "選擇後，我們會把故事線安排進你的正常路線；不參加也不影響基礎行程服務。",
    open: "選擇這條故事線",
    decline: "這次不參加故事",
    required: "多日行程需要選擇故事安排在第幾天。",
    limit: "每一天最多安排一條故事；如需選擇更多故事，請增加行程天數。",
    chooseDay: "請選擇日期",
    dayLabel: "安排故事日期",
    dayOption: (day: number, date: string) => `第 ${day} 天 · ${date}`,
    hours: (hours: number) => `約 ${hours} 小時`,
    regions: { peninsula: "澳門半島", taipa: "氹仔", coloane: "路環" },
    stories: {
      lotus_city_double_map: { title: "蓮城雙圖：未盡之圖", subtitle: "沿六處真實地點，讀懂兩張記錄不同真實的澳門地圖" },
      taipa_letters: { title: "海風寄來的信", subtitle: "沿氹仔舊城尋找五封沒有收件人的信，讀見島上的家與生活" },
      coloane_after_tide: { title: "潮退之後", subtitle: "沿路環村、古廟、船廠與黑沙，補完一本沒有寫完的潮汐工作簿" },
    },
  },
  en: {
    eyebrow: "Story experience · optional",
    title: "Choose a Macau story",
    lead: "Choose one and we will place its authored route into your regular itinerary. Skipping it will not affect core trip services.",
    open: "Choose this story",
    decline: "No story this trip",
    required: "Choose which day of your multi-day trip should include the story.",
    limit: "Only one story can be scheduled per day. Add another trip day to choose more.",
    chooseDay: "Choose a day",
    dayLabel: "Schedule this story",
    dayOption: (day: number, date: string) => `Day ${day} · ${date}`,
    hours: (hours: number) => `About ${hours} hours`,
    regions: { peninsula: "Macau Peninsula", taipa: "Taipa", coloane: "Coloane" },
    stories: {
      lotus_city_double_map: { title: "Two Maps of the Lotus City", subtitle: "Read two different records of Macau across six real places" },
      taipa_letters: { title: "Letters Carried by the Sea Breeze", subtitle: "Find five unaddressed letters across old Taipa and discover the island's homes and daily life" },
      coloane_after_tide: { title: "After the Tide", subtitle: "Complete an unfinished tidal workbook through Coloane village, temples, shipyards, and Hac Sa" },
    },
  },
  pt: {
    eyebrow: "Experiência narrativa · opcional",
    title: "Escolha uma história de Macau",
    lead: "Escolha uma história e integraremos o percurso no itinerário normal. Ignorá-la não afeta os serviços essenciais.",
    open: "Escolher esta história",
    decline: "Sem história nesta viagem",
    required: "Escolha o dia da viagem de vários dias para realizar a história.",
    limit: "Só pode agendar uma história por dia. Adicione outro dia para escolher mais.",
    chooseDay: "Escolher um dia",
    dayLabel: "Agendar esta história",
    dayOption: (day: number, date: string) => `Dia ${day} · ${date}`,
    hours: (hours: number) => `Cerca de ${hours} horas`,
    regions: { peninsula: "Península de Macau", taipa: "Taipa", coloane: "Coloane" },
    stories: {
      lotus_city_double_map: { title: "Dois Mapas da Cidade de Lótus", subtitle: "Leia dois registos diferentes de Macau ao longo de seis lugares reais" },
      taipa_letters: { title: "Cartas trazidas pela brisa do mar", subtitle: "Encontre cinco cartas sem destinatário pela Taipa antiga e descubra as casas e a vida da ilha" },
      coloane_after_tide: { title: "Depois da Maré", subtitle: "Complete um caderno de marés inacabado pela vila, templos, estaleiros e Hac Sá" },
    },
  },
} as const;

function addDays(date: string, offset: number): string {
  const parsed = new Date(`${date}T00:00:00`);
  parsed.setDate(parsed.getDate() + offset);
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function StoryChoiceSection({
  language,
  multiDay,
  tripDays,
  arrivalDate,
  storyOptIn,
  storyId,
  storyDay,
  storySelections,
  disabled,
  onDecline,
  onSelectStory,
  onDayChange,
  onStoryDayChange,
}: {
  language: LanguageCode;
  multiDay: boolean;
  tripDays: number;
  arrivalDate: string;
  storyOptIn: boolean | null;
  storyId: StoryId | null | undefined;
  storyDay: number | null;
  storySelections?: StorySelection[];
  disabled?: boolean;
  onDecline: () => void;
  onSelectStory: (storyId: StoryId) => void;
  onDayChange: (day: number | null) => void;
  onStoryDayChange?: (storyId: StoryId, day: number | null) => void;
}) {
  const copy = COPY[language] ?? COPY["zh-CN"];

  return (
    <section className="mb-10" aria-labelledby="story-choice-title">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
        {copy.eyebrow}
      </p>
      <h2 id="story-choice-title" className="mt-2 font-display text-2xl text-ink">
        {copy.title}
      </h2>
      <p className="mt-1 max-w-xl text-sm leading-relaxed text-ink-soft">{copy.lead}</p>

      <button
        type="button"
        disabled={disabled}
        onClick={onDecline}
        aria-pressed={storyOptIn === false}
        className={`mt-5 min-h-11 rounded-full border px-5 text-sm ${storyOptIn === false ? "border-sage-deep bg-sage-deep text-paper" : "border-line bg-card text-ink"}`}
      >
        {copy.decline}
      </button>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {STORIES.map((story) => {
          const localized = copy.stories[story.id];
          const scheduled = storySelections?.find((selection) => selection.story_id === story.id);
          const active = storySelections
            ? Boolean(scheduled)
            : storyOptIn === true && storyId === story.id;
          const selectionLimitReached = Boolean(
            multiDay && storySelections && !active && storySelections.length >= tripDays,
          );
          const cardDisabled = Boolean(disabled || selectionLimitReached);
          return (
            <article
              key={story.id}
              onClick={(event) => {
                if (cardDisabled || (event.target as HTMLElement).closest("button, select, option, label")) {
                  return;
                }
                onSelectStory(story.id);
              }}
              className={`flex h-full flex-col overflow-hidden rounded-lg border bg-card transition ${
                cardDisabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-sage-deep"
              } ${active ? "border-sage-deep ring-2 ring-sage-deep/20" : "border-line"}`}
            >
              <StoryImage
                assetId={story.assetId}
                alt={localized.title}
                className="!aspect-[4/3] rounded-none border-0"
                imageClassName="object-cover"
              />
              <div className="flex min-h-64 flex-1 flex-col p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sage-deep">
                  {copy.regions[story.region]} · {copy.hours(story.hours)}
                </p>
                <h3 className="mt-2 font-display text-xl leading-tight text-ink">{localized.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-soft">{localized.subtitle}</p>
                {multiDay && active ? (
                  <label className="mt-4 block text-xs font-medium text-ink">
                    <span className="mb-1.5 block">{copy.dayLabel}</span>
                    <select
                      value={scheduled?.story_day ?? storyDay ?? ""}
                      onChange={(event) => {
                        const day = event.target.value ? Number(event.target.value) : null;
                        if (onStoryDayChange) onStoryDayChange(story.id, day);
                        else onDayChange(day);
                      }}
                      disabled={disabled}
                      className="h-11 w-full rounded-lg border border-line bg-paper px-3 text-sm text-ink outline-none focus:border-sage-deep"
                    >
                      <option value="">{copy.chooseDay}</option>
                      {Array.from({ length: tripDays }, (_, index) => {
                        const day = index + 1;
                        return (
                          <option
                            key={day}
                            value={day}
                            disabled={storySelections?.some(
                              (selection) =>
                                selection.story_id !== story.id && selection.story_day === day,
                            )}
                          >
                            {copy.dayOption(day, addDays(arrivalDate, index))}
                          </option>
                        );
                      })}
                    </select>
                  </label>
                ) : null}
                <button
                  type="button"
                  disabled={cardDisabled}
                  onClick={() => onSelectStory(story.id)}
                  aria-pressed={active}
                  className={`mt-4 inline-flex min-h-11 items-center justify-center rounded-full px-4 text-center text-sm font-medium ${active ? "bg-sage-deep text-paper" : "border border-sage-deep text-sage-deep"}`}
                >
                  {copy.open}
                </button>
              </div>
            </article>
          );
        })}
      </div>
      {storyOptIn && multiDay && !storyDay ? (
        <p className="mt-3 text-sm text-clay" role="alert">{copy.required}</p>
      ) : null}
      {multiDay && storySelections && storySelections.length >= tripDays ? (
        <p className="mt-3 text-sm text-ink-soft">{copy.limit}</p>
      ) : null}
    </section>
  );
}
