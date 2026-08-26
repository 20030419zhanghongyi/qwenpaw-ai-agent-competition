import { NavLink } from "react-router-dom";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";
import { useStory } from "@/state/StoryContext";

const TABS = [
  { to: "/guide", labelKey: "navGuide" as const },
  { to: "/walk", labelKey: "navItinerary" as const },
  { to: "/profile", labelKey: "navProfile" as const },
];

function selectedStoryUrl(preference: ReturnType<typeof useWalk>["preference"]): string {
  if (!preference?.story_id) return "/stories";
  const base = `/stories/${preference.story_id}`;
  if (!preference.story_day || !preference.travel_date) return base;
  const date = new Date(`${preference.travel_date}T00:00:00`);
  date.setDate(date.getDate() + preference.story_day - 1);
  const scheduledDate = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
  return `${base}?${new URLSearchParams({ scheduledDay: String(preference.story_day), scheduledDate })}`;
}

export function AppNav() {
  const { language, preference } = useWalk();
  const { session } = useStory();
  const storySelected = preference?.story_opt_in === true && Boolean(preference.story_id);
  const matchingSession = session?.story_id === preference?.story_id ? session : null;
  const storyDestination = matchingSession
    ? matchingSession.status === "completed"
      ? `/story-sessions/${matchingSession.session_id}/ending`
      : matchingSession.current_chapter?.kind === "prologue"
        ? `/story-sessions/${matchingSession.session_id}/nodes/${matchingSession.current_chapter_id}`
        : `/story-sessions/${matchingSession.session_id}/map`
    : selectedStoryUrl(preference);
  const tabs = storySelected
    ? [TABS[0], { to: storyDestination, labelKey: "navStory" as const }, ...TABS.slice(1)]
    : TABS;

  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-paper/95 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <NavLink
          to="/guide"
          className="group flex shrink-0 items-center gap-2.5 text-ink no-underline"
        >
          <span className="grid size-8 place-items-center rounded-md bg-sage-deep font-serif text-sm font-bold text-paper transition group-hover:bg-moss">
            {t(language, "brandMark")}
          </span>
          <span className="hidden font-serif text-sm tracking-wide sm:inline">
            {t(language, "brandShort")}
          </span>
        </NavLink>

        <nav
          aria-label={t(language, "navAria")}
          className="flex flex-1 items-stretch justify-center gap-0 sm:gap-1"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                [
                  "relative flex min-w-0 flex-1 items-center justify-center px-2 py-3 text-sm transition sm:flex-none sm:px-5",
                  isActive
                    ? "font-medium text-sage-deep"
                    : "text-ink-soft hover:text-ink",
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  <span className="truncate">{t(language, tab.labelKey)}</span>
                  <span
                    aria-hidden
                    className={[
                      "absolute inset-x-3 bottom-0 h-0.5 origin-center rounded-full bg-sage-deep transition-transform duration-200 sm:inset-x-4",
                      isActive ? "scale-x-100" : "scale-x-0",
                    ].join(" ")}
                  />
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="hidden w-[7.5rem] shrink-0 sm:block" aria-hidden />
      </div>
    </header>
  );
}
