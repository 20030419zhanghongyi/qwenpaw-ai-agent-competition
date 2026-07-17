import { Link } from "react-router-dom";
import heroImg from "@/assets/hero-ruins.jpg";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

const LANGS = [
  { code: "zh-CN" as const, label: "简体中文", sub: "Simplified" },
  { code: "zh-TW" as const, label: "繁體中文", sub: "Traditional" },
  { code: "en" as const, label: "English", sub: "English" },
  { code: "pt" as const, label: "Português", sub: "Portuguese" },
];

export function LanguagePage() {
  const { language, setLanguage } = useWalk();

  const select = (code: LanguageCode) => {
    setLanguage(code);
  };

  return (
    <main className="flex min-h-dvh flex-1 flex-col bg-paper text-ink">
      <div className="grid min-h-dvh flex-1 w-full grid-cols-1 lg:grid-cols-[1.15fr_1fr]">
        <section className="relative isolate min-h-[48dvh] overflow-hidden bg-sage-deep lg:min-h-dvh">
          <img
            src={heroImg}
            alt={t(language, "heroAlt")}
            width={960}
            height={1024}
            className="absolute inset-0 h-full w-full object-cover opacity-90"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-paper/95 lg:bg-gradient-to-r lg:from-transparent lg:via-transparent lg:to-paper" />
          <div className="relative flex h-full min-h-[48dvh] flex-col justify-between p-6 lg:min-h-dvh lg:p-12">
            <div className="flex items-center gap-3 text-paper">
              <div className="grid size-9 place-items-center rounded-lg bg-paper/95 font-serif text-lg font-bold text-sage-deep">
                {t(language, "brandMark")}
              </div>
              <span className="font-serif text-sm uppercase tracking-[0.18em]">
                Macau · StoryWalk
              </span>
            </div>
            <div className="max-w-md space-y-3 pb-2 text-paper lg:pb-0">
              <p className="text-xs font-medium uppercase tracking-[0.24em] opacity-80">
                {t(language, "chapterI")}
              </p>
              <h2 className="font-display text-3xl leading-tight lg:text-5xl">
                {t(language, "heroTitleLine1")}
                <br />
                {t(language, "heroTitleLine2")}
              </h2>
              <p className="font-serif text-sm italic opacity-80">
                {t(language, "heroSubtitle")}
              </p>
            </div>
          </div>
        </section>

        <section className="flex min-h-dvh flex-col bg-paper lg:min-h-0">
          <AzulejoBand className="mt-6 shrink-0" />

          <div className="flex flex-1 flex-col px-6 py-8 lg:px-14 lg:py-12">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
              {t(language, "homeEyebrow")}
            </p>
            <h1 className="mb-4 font-display text-3xl leading-[1.15] text-ink lg:text-4xl">
              {t(language, "homeTitle")}
              <br />
              <span className="italic text-sage-deep">{t(language, "homeTitleAccent")}</span>
            </h1>
            <p className="mb-8 max-w-md text-sm leading-relaxed text-ink-soft">
              {t(language, "homeLead")}
            </p>

            <div className="space-y-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-ink-soft">
                {t(language, "selectLanguage")}
              </p>
              <ul className="space-y-2.5">
                {LANGS.map((l) => {
                  const active = language === l.code;
                  return (
                    <li key={l.code}>
                      <button
                        type="button"
                        onClick={() => select(l.code)}
                        aria-pressed={active}
                        className={`group flex w-full items-center justify-between rounded-full border px-5 py-3.5 text-left transition-all ${
                          active
                            ? "border-sage-deep bg-sage-deep text-paper shadow-[var(--shadow-soft)]"
                            : "border-line bg-card hover:border-sage hover:bg-paper-warm"
                        }`}
                      >
                        <span className="flex items-baseline gap-3">
                          <span className="font-serif text-base font-medium">{l.label}</span>
                          <span
                            className={`text-[10px] uppercase tracking-widest ${
                              active ? "text-paper/60" : "text-ink-soft"
                            }`}
                          >
                            {l.sub}
                          </span>
                        </span>
                        <span aria-hidden className="text-lg">
                          →
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="mt-auto space-y-4 pt-10">
              <Link
                to="/preferences"
                className="block w-full rounded-full bg-sage-deep px-6 py-4 text-center font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
              >
                {t(language, "beginWalk")}
              </Link>
              <Link
                to="/guide"
                className="block w-full rounded-full border border-line bg-card px-6 py-3.5 text-center text-sm text-ink transition hover:border-sage"
              >
                {t(language, "navGuide")} →
              </Link>
              <p className="flex items-start gap-2 text-[11px] leading-relaxed text-ink-soft">
                <span aria-hidden className="mt-0.5">
                  🛡
                </span>
                <span>{t(language, "privacyNote")}</span>
              </p>
            </div>
          </div>

          <div className="calcada-wave mx-6 mb-6 h-2.5 shrink-0 opacity-60 lg:mx-14" />
        </section>
      </div>
    </main>
  );
}
