import { NavLink, useNavigate } from "react-router-dom";
import {
  isStoryId,
  localizedStoryTitle,
} from "@/features/story/storyMetadata";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";
import { useStory } from "@/state/StoryContext";
import type { Preference, StorySelection } from "@/types";

const TABS = [
  { to: "/guide", labelKey: "navGuide" as const },
  { to: "/walk", labelKey: "navItinerary" as const },
  { to: "/profile", labelKey: "navProfile" as const },
];

function selectedStoryUrl(
  preference: Preference | null,
  selection: StorySelection | null,
): string {
  if (!selection) return "/stories";
  const base = `/stories/${selection.story_id}`;
  if (!preference?.travel_date) return base;
  const date = new Date(`${preference.travel_date}T00:00:00`);
  date.setDate(date.getDate() + selection.story_day - 1);
  const scheduledDate = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
  return `${base}?${new URLSearchParams({ scheduledDay: String(selection.story_day), scheduledDate })}`;
}

export function AppNav() {
  const navigate = useNavigate();
  const {
    language,
    preference,
    activeItineraryDay,
    setActiveItineraryDay,
  } = useWalk();
  const { session } = useStory();
  const storySelections: StorySelection[] = (
    preference?.story_selections?.length
      ? preference.story_selections
      : preference?.story_id && isStoryId(preference.story_id)
        ? [{ story_id: preference.story_id, story_day: preference.story_day ?? 1 }]
        : []
  )
    .filter((selection): selection is StorySelection => isStoryId(selection.story_id))
    .sort((left, right) => left.story_day - right.story_day);
  const storySelected = preference?.story_opt_in === true && storySelections.length > 0;
  const activeStorySelection = storySelections.find(
    (selection) => selection.story_day === activeItineraryDay,
  ) ?? storySelections[0] ?? null;

  const storyDestinationFor = (selection: StorySelection | null) => {
    const matchingSession = selection && session?.story_id === selection.story_id ? session : null;
    return matchingSession
      ? matchingSession.status === "completed"
        ? `/story-sessions/${matchingSession.session_id}/ending`
        : matchingSession.current_chapter?.kind === "prologue"
          ? `/story-sessions/${matchingSession.session_id}/nodes/${matchingSession.current_chapter_id}`
          : `/story-sessions/${matchingSession.session_id}/map`
      : selectedStoryUrl(preference, selection);
  };
  const storyDestination = storyDestinationFor(activeStorySelection);
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
          {tabs.map((tab) => {
            const isStoryTab = tab.labelKey === "navStory";
            if (isStoryTab && activeStorySelection) {
              return (
                <div
                  key="story-navigation"
                  className="relative flex min-w-0 flex-1 items-center justify-center sm:flex-none"
                >
                  <NavLink
                    to={storyDestination}
                    className="relative flex h-full items-center px-1 py-3 text-sm text-ink-soft transition hover:text-ink sm:px-2"
                  >
                    {t(language, "navStory")}
                  </NavLink>
                  {storySelections.length > 1 ? (
                    <select
                      aria-label={`${t(language, "navStory")} · ${t(language, "dayN").replace("{n}", String(activeStorySelection.story_day))}`}
                      value={activeStorySelection.story_day}
                      onChange={(event) => {
                        const day = Number(event.target.value);
                        const selection = storySelections.find(
                          (candidate) => candidate.story_day === day,
                        );
                        if (!selection) return;
                        setActiveItineraryDay(day);
                        navigate(storyDestinationFor(selection));
                      }}
                      className="max-w-24 rounded-md border border-line bg-card py-1 pl-1.5 pr-5 text-[11px] text-sage-deep outline-none focus:border-sage-deep sm:max-w-48 sm:text-xs"
                    >
                      {storySelections.map((selection) => (
                        <option key={`${selection.story_day}-${selection.story_id}`} value={selection.story_day}>
                          {t(language, "dayN").replace("{n}", String(selection.story_day))} · {localizedStoryTitle(selection.story_id, language)}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>
              );
            }
            return (
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
            );
          })}
        </nav>

        <div className="hidden w-[7.5rem] shrink-0 sm:block" aria-hidden />
      </div>
    </header>
  );
}
