import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/state/AuthContext";
import { useWalk } from "@/state/WalkContext";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";

type Mode = "login" | "register";

/** Common countries for the country selector (ISO 3166-1 alpha-2). */
const COUNTRIES: { code: string; label: Record<LanguageCode, string> }[] = [
  { code: "CN", label: { "zh-CN": "中国大陆", "zh-TW": "中國大陸", en: "China", pt: "China" } },
  { code: "HK", label: { "zh-CN": "中国香港", "zh-TW": "中國香港", en: "Hong Kong", pt: "Hong Kong" } },
  { code: "MO", label: { "zh-CN": "中国澳门", "zh-TW": "中國澳門", en: "Macau", pt: "Macau" } },
  { code: "TW", label: { "zh-CN": "中国台湾", "zh-TW": "中國台灣", en: "Taiwan", pt: "Taiwan" } },
  { code: "JP", label: { "zh-CN": "日本", "zh-TW": "日本", en: "Japan", pt: "Japão" } },
  { code: "KR", label: { "zh-CN": "韩国", "zh-TW": "韓國", en: "South Korea", pt: "Coreia do Sul" } },
  { code: "SG", label: { "zh-CN": "新加坡", "zh-TW": "新加坡", en: "Singapore", pt: "Singapura" } },
  { code: "MY", label: { "zh-CN": "马来西亚", "zh-TW": "馬來西亞", en: "Malaysia", pt: "Malásia" } },
  { code: "TH", label: { "zh-CN": "泰国", "zh-TW": "泰國", en: "Thailand", pt: "Tailândia" } },
  { code: "PH", label: { "zh-CN": "菲律宾", "zh-TW": "菲律賓", en: "Philippines", pt: "Filipinas" } },
  { code: "US", label: { "zh-CN": "美国", "zh-TW": "美國", en: "United States", pt: "Estados Unidos" } },
  { code: "GB", label: { "zh-CN": "英国", "zh-TW": "英國", en: "United Kingdom", pt: "Reino Unido" } },
  { code: "PT", label: { "zh-CN": "葡萄牙", "zh-TW": "葡萄牙", en: "Portugal", pt: "Portugal" } },
  { code: "FR", label: { "zh-CN": "法国", "zh-TW": "法國", en: "France", pt: "França" } },
  { code: "DE", label: { "zh-CN": "德国", "zh-TW": "德國", en: "Germany", pt: "Alemanha" } },
  { code: "AU", label: { "zh-CN": "澳大利亚", "zh-TW": "澳洲", en: "Australia", pt: "Austrália" } },
  { code: "CA", label: { "zh-CN": "加拿大", "zh-TW": "加拿大", en: "Canada", pt: "Canadá" } },
  { code: "BR", label: { "zh-CN": "巴西", "zh-TW": "巴西", en: "Brazil", pt: "Brasil" } },
];

const LANGUAGE_LABELS: Record<LanguageCode, string> = {
  "zh-CN": "简体中文",
  "zh-TW": "繁體中文",
  en: "English",
  pt: "Português",
};

export function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, register, error, clearError, isAuthenticated, isRestoring } = useAuth();
  const { language } = useWalk();

  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const requestedReturnTo = searchParams.get("returnTo");
  const returnTo =
    requestedReturnTo?.startsWith("/") && !requestedReturnTo.startsWith("//")
      ? requestedReturnTo
      : "/preferences";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isRestoring && isAuthenticated) {
      navigate(returnTo, { replace: true });
    }
  }, [isAuthenticated, isRestoring, navigate, returnTo]);

  const changeMode = (nextMode: Mode) => {
    setMode(nextMode);
    clearError();
    setFormError(null);
  };

  const goBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate("/", { replace: true });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim() || null;
    const normalizedPhone = phone.trim() || null;
    if (!normalizedEmail && !normalizedPhone) {
      setFormError(t(language, "authEmailOrPhone"));
      return;
    }
    if (!password.trim()) {
      setFormError(t(language, "authPasswordRequired"));
      return;
    }
    setFormError(null);

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ email: normalizedEmail, phone: normalizedPhone, password: password });
      } else {
        const normalizedName = name.trim();
        if (!normalizedName) return;
        if (password !== confirmPassword) {
          setFormError(t(language, "authPasswordMismatch"));
          return;
        }
        await register({
          email: normalizedEmail,
          phone: normalizedPhone,
          password,
          name: normalizedName,
          language,
          country: country || null,
        });
      }
      navigate(returnTo);
    } catch {
      // The provider exposes the backend error for display.
    } finally {
      setSubmitting(false);
    }
  };

  if (isRestoring) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
        <p className="text-sm text-ink-soft">{t(language, "restoringSession")}</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8">
        <button
          type="button"
          onClick={goBack}
          className="text-sm text-ink-soft transition hover:text-ink"
        >
          {t(language, "back")}
        </button>
        <h1 className="mt-4 font-display text-3xl text-ink">
          {mode === "login" ? t(language, "authLoginTab") : t(language, "authRegisterTab")}
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          {t(language, "authPrompt")}
        </p>

        {/* Mode toggle */}
        <div className="mt-6 grid grid-cols-2 rounded-full bg-paper-warm p-1">
          <button
            type="button"
            onClick={() => changeMode("login")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "login" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            {t(language, "authLoginTab")}
          </button>
          <button
            type="button"
            onClick={() => changeMode("register")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "register" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            {t(language, "authRegisterTab")}
          </button>
        </div>

        <form className="mt-6 space-y-4" onSubmit={(event) => void submit(event)}>
          {/* Email */}
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">{t(language, "authEmail")}</span>
            <input
              type="email"
              value={email}
              onChange={(event) => { setEmail(event.target.value); setFormError(null); }}
              placeholder={t(language, "authEmailPlaceholder")}
              className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
              autoComplete="email"
            />
          </label>

          {/* Phone */}
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">{t(language, "authPhone")}</span>
            <input
              type="tel"
              value={phone}
              onChange={(event) => { setPhone(event.target.value); setFormError(null); }}
              placeholder={t(language, "authPhonePlaceholder")}
              className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
              autoComplete="tel"
            />
          </label>

          {/* Password — both modes */}
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">{t(language, "authPassword")}</span>
            <input
              required
              type="password"
              value={password}
              onChange={(event) => { setPassword(event.target.value); setFormError(null); }}
              placeholder={mode === "register" ? t(language, "authPasswordPlaceholder") : t(language, "authPasswordPlaceholderLogin")}
              className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
              autoComplete={mode === "register" ? "new-password" : "current-password"}
            />
          </label>

          {mode === "register" ? (
            <>
              {/* Confirm password */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authConfirmPassword")}</span>
                <input
                  required
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => { setConfirmPassword(event.target.value); setFormError(null); }}
                  placeholder={t(language, "authConfirmPasswordPlaceholder")}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                  autoComplete="new-password"
                />
              </label>

              {/* Nickname */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authNickname")}</span>
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={t(language, "authNicknamePlaceholder")}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                  autoComplete="name"
                />
              </label>

              {/* Country */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authCountry")}</span>
                <select
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                >
                  <option value="">{t(language, "authCountryPlaceholder")}</option>
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label[language] ?? c.label["zh-CN"]}
                    </option>
                  ))}
                </select>
              </label>

              {/* Language */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "selectLanguage")}</span>
                <select
                  disabled
                  value={language}
                  className="h-11 w-full rounded-xl border border-line bg-paper-warm px-4 text-ink-soft outline-none"
                >
                  {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-ink-soft">
                  {t(language, "languageFromHome")}
                </p>
              </label>
            </>
          ) : null}

          {formError ? (
            <p role="alert" className="text-sm text-clay">
              {formError}
            </p>
          ) : error ? (
            <p role="alert" className="text-sm text-clay">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="h-12 w-full rounded-full bg-sage-deep font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {submitting
              ? t(language, "submitting")
              : mode === "login"
                ? t(language, "authLoginButton")
                : t(language, "authRegisterButton")}
          </button>
        </form>

        {/* Toggle hint */}
        <p className="mt-4 text-center text-sm text-ink-soft">
          {mode === "login" ? (
            <button
              type="button"
              onClick={() => changeMode("register")}
              className="underline transition hover:text-ink"
            >
              {t(language, "authToggleToRegister")}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => changeMode("login")}
              className="underline transition hover:text-ink"
            >
              {t(language, "authToggleToLogin")}
            </button>
          )}
        </p>
      </section>
    </main>
  );
}
