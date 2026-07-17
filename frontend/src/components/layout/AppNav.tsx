import { NavLink } from "react-router-dom";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";

const TABS = [
  { to: "/guide", labelKey: "navGuide" as const },
  { to: "/walk", labelKey: "navItinerary" as const },
  { to: "/profile", labelKey: "navProfile" as const },
];

export function AppNav() {
  const { language } = useWalk();

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
          {TABS.map((tab) => (
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
